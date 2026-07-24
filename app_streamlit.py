import streamlit as st
import datetime
import urllib.parse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from datastore import db
from app.services import QRService, CardService, AIService

# MUST be the first Streamlit command
st.set_page_config(page_title="ReviewQR Automation", layout="wide", initial_sidebar_state="expanded")

def inject_compact_css():
    st.markdown("""
        <style>
        /* Reduce top and bottom page padding */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        /* Tighten vertical spacing between all elements */
        div[data-testid="stVerticalBlock"] > div {
            padding-top: 0.3rem !important;
            padding-bottom: 0.3rem !important;
        }
        /* Reduce element container margins */
        .element-container {
            margin-bottom: 0.4rem !important;
        }
        /* Tighten metric spacing */
        div[data-testid="metric-container"] {
            padding: 12px 18px !important;
        }
        /* Tighten horizontal columns spacing */
        div[data-testid="column"] {
            padding: 0px 8px !important;
        }
        /* Shrink st.container(border=True) padding */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 0.3rem 0.6rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 0px !important;
        }
        /* Vertically align text and button inside services columns */
        div[data-testid="column"] p {
            margin-top: 6px !important;
            margin-bottom: 0px !important;
        }
        </style>
    """, unsafe_allow_html=True)

inject_compact_css()

def client_review_page(token):
    req = db.get_request(token)
    if not req or not req.get("is_active"):
        st.error("Invalid or expired review request link.")
        return

    # Log scan on first load
    if "scanned" not in st.session_state:
        db.log_scan(token)
        st.session_state["scanned"] = True

    client_name = req.get("client_name") or "Your Business Name"
    client_industry = req.get("client_industry") or "Your Industry"
    place_id = req.get("google_place_id") or db.get_setting("google_place_id", "")
    
    # Parse allowed services
    allowed_ids = [int(x.strip()) for x in req.get("allowed_services", "").split(",") if x.strip().isdigit()]
    all_services = db.get_services()
    offered_services = [s for s in all_services if s["id"] in allowed_ids]

    # Use columns to perfectly center the client view on desktop
    _, center_col, _ = st.columns([1, 2, 1])
    
    with center_col:
        st.markdown(f"<h2 style='text-align: center; color: #2c5364; font-size: 1.8rem; margin-bottom: 0;'>Review {client_name}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: #718096; font-size: 0.95rem; margin-bottom: 5px;'>Thanks for choosing us for {client_industry}!</p>", unsafe_allow_html=True)
        st.divider()
        
        st.write("**🌟 Rate Your Experience**")
        
        if not offered_services:
            st.warning("No specific services are configured for this review.")
            offered_services = all_services

        service_options = {s["name"]: s["id"] for s in offered_services}
        selected_service_name = st.selectbox("What service did you receive?", list(service_options.keys()))
        
        # Rating & Email side-by-side to save height
        col_rate, col_email = st.columns([3, 2])
        with col_rate:
            rating = st.radio("How would you rate it?", ["Excellent", "Good", "Poor"], horizontal=True)
        with col_email:
            email = st.text_input("Your Email (Optional)")
        
        st.write("")
        if st.button("✨ Generate AI Review", type="primary", use_container_width=True):
            if not db.validate_email_submission(email):
                st.error("You can only submit one review every 30 days.")
            else:
                with st.spinner("Crafting the perfect review..."):
                    service_id = service_options[selected_service_name]
                    ai_text = AIService.generate_review_text(client_name, selected_service_name, rating)
                    db.submit_review(token, service_id, rating, email, ai_text)
                    st.session_state[f"review_text_{token}"] = ai_text
                    st.success("Review generated successfully!")

        # Display generated text
        if f"review_text_{token}" in st.session_state:
            current_text = st.session_state[f"review_text_{token}"]
            
            st.write("**💬 Your Review**")
            st.text_area("Long-press the text below to copy it:", value=current_text, height=120, label_visibility="collapsed")
            
            if place_id:
                google_url = f"https://search.google.com/local/writereview?placeid={place_id}"
                st.link_button("🚀 Proceed to Google Maps", google_url, type="primary", use_container_width=True)
                st.caption("Since you are on a local network, automatic copying is blocked by your phone's security. Please manually select and copy the text above, then click the button to go to Google Maps and paste it!")
            else:
                st.warning("Google Place ID not configured by admin. Please copy the text above and post it manually on Google.")


def page_dashboard():
    st.title("📊 Dashboard Overview")
    st.subheader("Performance Metrics")
    stats = db.get_dashboard_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True):
            st.metric("Total Requests", stats["total_requests"])
    with col2:
        with st.container(border=True):
            st.metric("Total Scans", stats["total_scans"])
    with col3:
        with st.container(border=True):
            st.metric("Submissions", stats["total_submissions"])
    with col4:
        with st.container(border=True):
            st.metric("Conversion Rate", f"{stats['conversion_rate']:.1f}%")
    
    st.divider()
    st.subheader("Recent Client Feedback")
    if not stats["recent_reviews"]:
        st.info("No feedback submitted yet.")
    else:
        # Render feedback in a 2-column layout to save vertical space
        fb_cols = st.columns(2)
        for idx, r in enumerate(stats["recent_reviews"]):
            col_idx = idx % 2
            with fb_cols[col_idx]:
                with st.container(border=True):
                    st.markdown(f"**{r['rating']} - {r['service_name']}**")
                    st.markdown(f"*{r['ai_generated_text']}*")
                    email_str = f" | {r['email']}" if r.get('email') else ""
                    st.caption(f"{r['created_at']}{email_str}")

def page_generate_qr():
    st.title("✨ Generate Dynamic Review QR")
    
    with st.container(border=True):
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.write("**Client & QR Details**")
            # Side-by-side client details
            c_name_col, c_ind_col = st.columns(2)
            client_name = c_name_col.text_input("Client Name", placeholder="e.g. Acme Corp")
            client_industry = c_ind_col.text_input("Sub-Industry", placeholder="e.g. Software Services")
            
            # Side-by-side contact/place info
            place_col, phone_col = st.columns(2)
            place_id = place_col.text_input("Google Place ID (Optional override)", placeholder="ChIJN1t...")
            phone_num = phone_col.text_input("Card Phone Number", value=db.get_setting("default_phone", "0000000000"))
            
            st.link_button("🔍 Find Google Place ID", "https://developers.google.com/maps/documentation/javascript/examples/places-placeid-finder", use_container_width=True)
            
        with col2:
            st.write("**Select Services to offer for review**")
            all_services = db.get_services()
            selected_services = []
            
            # Render checkboxes in a 2-column grid to cut height in half
            with st.container(border=True):
                s_cols = st.columns(2)
                for idx, s in enumerate(all_services):
                    col_idx = idx % 2
                    with s_cols[col_idx]:
                        if st.checkbox(s["name"], key=f"srv_{s['id']}"):
                            selected_services.append(str(s["id"]))
                        
        st.write("")
        if st.button("🚀 Generate QR & Print Cards", type="primary", use_container_width=True):
            if not client_name:
                st.error("Please provide a Client Name")
            elif not selected_services:
                st.error("Please select at least one service")
            else:
                allowed_ids = ",".join(selected_services)
                req = db.create_review_request(client_name, client_industry, place_id, allowed_ids, phone=phone_num)
                
                import socket
                import os
                
                # Check for BASE_URL in environment (useful for VPS subdomain deployment)
                base_url = os.getenv("BASE_URL")
                if not base_url:
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    base_url = f"http://{local_ip}:8501"
                
                st.success("QR Generated Successfully!")
                url = f"{base_url}/?token={req['token']}"
                
                st.markdown(f"**Direct Link:** `{url}`")
                
                # Show QR and Card downloads
                qr_bytes = QRService.generate_qr_bytes(req['token'], base_url)
                card_bytes = CardService.generate_card(req['token'], base_url, client_name, client_industry, phone=req.get("phone", "0000000000"))
                
                st.divider()
                
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    st.image(qr_bytes, width=250, caption="Standard QR Code")
                    st.download_button("📥 Download QR (PNG)", qr_bytes, file_name=f"qr_{req['token']}.png", mime="image/png")
                with col_dl2:
                    st.image(card_bytes, width=200, caption="Premium Print Card")
                    st.download_button("📥 Download Card (PNG)", card_bytes, file_name=f"card_{req['token']}.png", mime="image/png", type="primary")

def page_manage_services():
    st.title("🛠️ Manage Configurable Services")
    
    # Compact Add Service Form
    with st.form("new_service", border=True):
        col_input, col_btn = st.columns([4, 1])
        with col_input:
            new_s_name = st.text_input("Service Name", placeholder="e.g. Graphic Design", label_visibility="collapsed")
        with col_btn:
            submit = st.form_submit_button("➕ Add Service", type="primary", use_container_width=True)
        if submit and new_s_name:
            db.add_service(new_s_name)
            st.rerun()
                
    st.write("") # Spacing
    st.subheader("Current Services")
    all_services = db.get_services()
    
    if not all_services:
        st.info("No services configured yet.")
        return
        
    # Render services in a compact 3-column grid to prevent vertical scrolling
    cols = st.columns(3)
    for i, s in enumerate(all_services):
        col_idx = i % 3
        with cols[col_idx]:
            with st.container(border=True):
                # Thin column layout for service name & tiny delete trashcan
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"**{s['name']}**")
                if c2.button("🗑️", key=f"del_{s['id']}", help="Delete Service", use_container_width=True):
                    db.remove_service(s['id'])
                    st.rerun()

def page_global_settings():
    st.title("🌎 Global System Configuration")
    curr_place_id = db.get_setting("google_place_id", "")
    curr_phone = db.get_setting("default_phone", "0000000000")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            new_place_id = st.text_input("Global Google Place ID", curr_place_id, placeholder="ChIJN1t...")
            st.link_button("🔍 Find Google Place ID", "https://developers.google.com/maps/documentation/javascript/examples/places-placeid-finder", use_container_width=True)
        with col2:
            new_phone = st.text_input("Global Default Phone Number", curr_phone, placeholder="e.g. 0000000000")
            
        st.write("")
        if st.button("💾 Save Settings", type="primary", use_container_width=True):
            db.set_setting("google_place_id", new_place_id)
            db.set_setting("default_phone", new_phone)
            st.success("Settings saved successfully!")

def admin_dashboard():
    # Setup native Streamlit multi-page navigation
    pg1 = st.Page(page_dashboard, title="Dashboard Overview", icon="📊")
    pg2 = st.Page(page_generate_qr, title="Generate QR", icon="✨")
    pg3 = st.Page(page_manage_services, title="Manage Services", icon="🛠️")
    pg4 = st.Page(page_global_settings, title="Global Settings", icon="🌎")
    
    pg = st.navigation([pg1, pg2, pg3, pg4])
    
    # Custom sidebar headers
    st.sidebar.markdown("## ReviewQR | AI Admin")
    st.sidebar.caption("System v2.0")
    
    pg.run()


# Main execution flow
token = st.query_params.get("token")
if token:
    client_review_page(token)
else:
    admin_dashboard()

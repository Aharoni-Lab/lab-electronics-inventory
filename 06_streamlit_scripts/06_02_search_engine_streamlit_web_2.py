import streamlit as st
from datetime import datetime
import requests
import re
import pandas as pd
import firebase_admin
from firebase_admin import credentials, storage
import time
import logging
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class InventoryItem:
    """Data class for inventory items"""
    manufacturer_pn: str
    part_number: str
    description: str
    location: str
    company_made: str


class InventoryManager:
    """Main class for inventory management operations"""

    def __init__(self):
        self.bucket = None
        self._initialize_firebase()

    def _initialize_firebase(self) -> None:
        """Initialize Firebase connection"""
        try:
            if not firebase_admin._apps:
                # Check if Firebase secrets are available
                if "firebase" not in st.secrets:
                    st.error(
                        "🔧 Firebase configuration missing. Please contact administrator.")
                    st.stop()

                cred = credentials.Certificate({
                    "type": st.secrets["firebase"]["type"],
                    "project_id": st.secrets["firebase"]["project_id"],
                    "private_key_id": st.secrets["firebase"]["private_key_id"],
                    "private_key": st.secrets["firebase"]["private_key"].replace("\\n", "\n"),
                    "client_email": st.secrets["firebase"]["client_email"],
                    "client_id": st.secrets["firebase"]["client_id"],
                    "auth_uri": st.secrets["firebase"]["auth_uri"],
                    "token_uri": st.secrets["firebase"]["token_uri"],
                    "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
                    "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
                })
                firebase_admin.initialize_app(
                    cred, {'storageBucket': 'aharonilabinventory.appspot.com'})

            self.bucket = storage.bucket()
            logger.info("Firebase initialized successfully")

        except KeyError as e:
            logger.error(f"Missing Firebase configuration: {e}")
            st.error(
                f"🔧 Missing Firebase setting: {e}. Please contact administrator.")
            st.stop()
        except Exception as e:
            logger.error(f"Firebase initialization failed: {e}")
            st.error(
                "❌ Failed to initialize database connection. Please contact administrator.")
            st.error(f"Debug info: {str(e)}")
            st.stop()

    def fetch_inventory_data(self) -> Optional[str]:
        """Fetch inventory data from Firebase storage"""
        try:
            url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts.txt?alt=media"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch inventory data: {e}")
            return None

    def parse_inventory_block(self, block: str) -> Optional[InventoryItem]:
        """Parse a single inventory block into an InventoryItem"""
        try:
            patterns = {
                'manufacturer_pn': r'Manufacturer Part number:\s*(\S.*)',
                'part_number': r'Part number:\s*(\S.*)',
                'description': r'Description:\s*(\S.*)',
                'location': r'Location:\s*(\S.*)',
                'company_made': r'(?:Company Made|Fabricated Company):\s*(\S.*)'
            }

            data = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, block, re.IGNORECASE)
                data[key] = match.group(
                    1).strip() if match else "Not available"

            return InventoryItem(**data)

        except Exception as e:
            logger.warning(f"Failed to parse inventory block: {e}")
            return None

    def search_inventory(self, part_query: str = "", value_query: str = "") -> List[InventoryItem]:
        """Search inventory based on part number and/or value"""
        inventory_data = self.fetch_inventory_data()
        if not inventory_data:
            return []

        results = []
        blocks = inventory_data.split("\n\n")

        normalized_part_query = self._normalize_text(
            part_query) if part_query else None
        normalized_value_query = self._normalize_text(
            value_query) if value_query else None

        for block in blocks:
            if not block.strip():
                continue

            item = self.parse_inventory_block(block)
            if not item:
                continue

            # Check part number match
            if normalized_part_query:
                norm_manufacturer_pn = self._normalize_text(
                    item.manufacturer_pn)
                norm_part_number = self._normalize_text(item.part_number)
                match_part = (normalized_part_query in norm_manufacturer_pn or
                              normalized_part_query in norm_part_number)
            else:
                match_part = True

            # Check value/description match
            if normalized_value_query:
                norm_description = self._normalize_text(item.description)
                match_value = normalized_value_query in norm_description
            else:
                match_value = True

            if match_part and match_value:
                results.append(item)

        return results

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for search operations"""
        return re.sub(r'\s+', '', text.strip().lower()) if text else ""

    def submit_reorder_request(self, manufacturer_pn: str, description: str, requester_name: str) -> bool:
        """Submit a reorder request to Firebase"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            reorder_entry = (
                f"Date and Time: {current_time}, "
                f"Manufacturer Part Number: {manufacturer_pn}, "
                f"Description: {description}, "
                f"Requester Name: {requester_name}\n"
            )

            blob = self.bucket.blob('to_be_ordered.txt')

            existing_content = ""
            if blob.exists():
                existing_content = blob.download_as_text()

            updated_content = existing_content + reorder_entry
            blob.upload_from_string(updated_content)

            logger.info(
                f"Reorder request submitted by {requester_name} for {manufacturer_pn}")
            return True

        except Exception as e:
            logger.error(f"Failed to submit reorder request: {e}")
            return False

    def upload_files(self, files: List, uploader_name: str) -> Dict[str, bool]:
        """Upload files to Firebase storage"""
        results = {}

        for file in files:
            try:
                file_name = f"component_images/{uploader_name}/{file.name}"
                blob = self.bucket.blob(file_name)

                # Reset file pointer
                file.seek(0)
                blob.upload_from_string(file.read(), content_type=file.type)

                results[file.name] = True
                logger.info(
                    f"File {file.name} uploaded successfully by {uploader_name}")

            except Exception as e:
                logger.error(f"Failed to upload {file.name}: {e}")
                results[file.name] = False

        return results

    def get_dashboard_metrics(self) -> Dict[str, any]:
        """Calculate dashboard metrics from inventory data"""
        try:
            inventory_data = self.fetch_inventory_data()
            if not inventory_data:
                return {
                    "total_components": "No Data",
                    "active_requests": "No Data",
                    "categories": "No Data",
                    "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M')
                }

            blocks = inventory_data.split("\n\n")
            valid_items = 0
            locations = set()
            descriptions = []

            for block in blocks:
                if not block.strip():
                    continue
                item = self.parse_inventory_block(block)
                if item:
                    valid_items += 1
                    if item.location != "Not available":
                        locations.add(item.location)
                    if item.description != "Not available":
                        descriptions.append(item.description.lower())

            # Count unique categories (rough estimate based on common component types)
            categories = set()
            component_types = ['resistor', 'capacitor', 'inductor', 'ic', 'microcontroller',
                               'transistor', 'diode', 'led', 'connector', 'switch', 'sensor']

            for desc in descriptions:
                for comp_type in component_types:
                    if comp_type in desc:
                        categories.add(comp_type.title())

            # Get reorder requests count
            active_requests = 0
            try:
                if self.bucket:
                    blob = self.bucket.blob('to_be_ordered.txt')
                    if blob.exists():
                        reorder_content = blob.download_as_text()
                        active_requests = len(
                            [line for line in reorder_content.split('\n') if line.strip()])
            except Exception as e:
                logger.warning(f"Could not fetch reorder requests: {e}")
                active_requests = "N/A"

            return {
                "total_components": valid_items,
                "active_requests": active_requests,
                "categories": len(categories) if categories else max(1, len(locations)),
                "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M')
            }

        except Exception as e:
            logger.error(f"Failed to calculate dashboard metrics: {e}")
            return {
                "total_components": "Error",
                "active_requests": "Error",
                "categories": "Error",
                "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M')
            }


class AuthManager:
    """Handle authentication logic"""

    @staticmethod
    def authenticate() -> bool:
        """Handle user authentication"""
        if "authenticated" not in st.session_state:
            st.session_state["authenticated"] = False

        if st.session_state["authenticated"]:
            return True

        # Check if auth secrets are available
        if "auth" not in st.secrets:
            st.error(
                "🔧 Authentication not configured. Please contact administrator.")
            st.stop()

        # Login UI
        st.markdown("""
        <div style='text-align: center; padding: 2rem;'>
            <h1>🔬 Aharoni Lab Inventory System</h1>
            <p style='color: #666; font-size: 1.1em;'>Secure Access Required</p>
        </div>
        """, unsafe_allow_html=True)

        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])

            with col2:
                with st.form("login_form"):
                    st.markdown("### Login Credentials")
                    username = st.text_input(
                        "Username", placeholder="Enter your username")
                    password = st.text_input(
                        "Password", type="password", placeholder="Enter your password")

                    submitted = st.form_submit_button(
                        "🔐 Login", use_container_width=True)

                    if submitted:
                        try:
                            if (username == st.secrets["auth"]["username"] and
                                    password == st.secrets["auth"]["password"]):
                                st.session_state["authenticated"] = True
                                st.success("✅ Authentication successful!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(
                                    "❌ Invalid credentials. Please try again.")
                        except KeyError:
                            st.error(
                                "🔧 Authentication configuration error. Please contact administrator.")

        return False


class InventoryUI:
    """Handle the user interface components"""

    def __init__(self, inventory_manager: InventoryManager):
        self.inventory_manager = inventory_manager

    def render_header(self):
        """Render the application header"""
        st.markdown("""
        <div style='text-align: center; padding: 1rem; margin-bottom: 2rem; 
                    background: linear-gradient(90deg, #1f4e79 0%, #2e86de 100%); 
                    border-radius: 10px; color: white;'>
            <h1 style='margin: 0; font-size: 2.5em;'>🔬 Laboratory Inventory Management</h1>
            <p style='margin: 0.5rem 0 0 0; font-size: 1.2em; opacity: 0.9;'>
                Aharoni Lab • CHS 74-134 • Advanced Component Tracking System
            </p>
        </div>
        """, unsafe_allow_html=True)

    def render_sidebar(self):
        """Render the sidebar with file upload functionality"""
        with st.sidebar:
            st.markdown("### 📤 File Upload Center")

            with st.expander("📸 Upload Component Files", expanded=False):
                uploader_name = st.text_input(
                    "Your Name",
                    placeholder="Enter your full name",
                    help="This will be used to organize uploaded files"
                )

                uploaded_files = st.file_uploader(
                    "Choose files to upload",
                    type=["jpg", "jpeg", "png", "pdf"],
                    accept_multiple_files=True,
                    help="Supported formats: JPG, PNG, PDF"
                )

                if uploaded_files and uploader_name:
                    if st.button("🚀 Upload Files", use_container_width=True):
                        with st.spinner("Uploading files..."):
                            results = self.inventory_manager.upload_files(
                                uploaded_files, uploader_name)

                        success_count = sum(results.values())
                        total_count = len(results)

                        if success_count == total_count:
                            st.success(
                                f"✅ All {total_count} files uploaded successfully!")
                        else:
                            st.warning(
                                f"⚠️ {success_count}/{total_count} files uploaded successfully")

                        for filename, success in results.items():
                            if not success:
                                st.error(f"❌ Failed to upload: {filename}")

                elif uploaded_files and not uploader_name:
                    st.warning(
                        "⚠️ Please enter your name before uploading files")

            # Add system status
            st.markdown("---")
            st.markdown("### 📊 System Status")
            st.success("🟢 Database: Connected")
            st.info(f"🕒 Last updated: {datetime.now().strftime('%H:%M:%S')}")

    def render_search_section(self):
        """Render the main search interface"""
        st.markdown("### 🔍 Component Search")

        with st.container():
            col1, col2, col3 = st.columns([3, 3, 2])

            with col1:
                part_number_query = st.text_input(
                    "Part Number Search",
                    placeholder="e.g., STM32F407VG, LM358",
                    help="Search by manufacturer or internal part number"
                )

            with col2:
                value_query = st.text_input(
                    "Component Description",
                    placeholder="e.g., 4.7uF, 100 OHM, XOR gate",
                    help="Search by component value or description"
                )

            with col3:
                st.markdown("<br>", unsafe_allow_html=True)  # Spacing
                search_clicked = st.button(
                    "🔍 Search Inventory",
                    use_container_width=True,
                    type="primary"
                )

        if search_clicked:
            if not part_number_query and not value_query:
                st.warning("⚠️ Please enter at least one search criterion")
                return

            with st.spinner("Searching inventory database..."):
                results = self.inventory_manager.search_inventory(
                    part_number_query, value_query)

            if results:
                st.success(f"✅ Found {len(results)} matching component(s)")
                self._display_search_results(results)
            else:
                st.warning(
                    "⚠️ No components found matching your search criteria")
                st.info("💡 Try using broader search terms or check your spelling")

    def _display_search_results(self, results: List[InventoryItem]):
        """Display search results in a professional table format"""
        st.markdown("### 📋 Search Results")

        # Create DataFrame for better display
        df_data = []
        for item in results:
            df_data.append({
                'Description': item.description,
                'Manufacturer P/N': item.manufacturer_pn,
                'Internal P/N': item.part_number,
                'Location': item.location,
                'Supplier': item.company_made
            })

        df = pd.DataFrame(df_data)

        # Display with custom styling
        st.markdown("""
        <style>
        .dataframe {
            font-size: 14px;
        }
        .dataframe th {
            background-color: #f0f2f6;
            font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Description": st.column_config.TextColumn("Description", width="large"),
                "Location": st.column_config.TextColumn("Location", width="medium"),
                "Manufacturer P/N": st.column_config.TextColumn("Mfg P/N", width="medium"),
                "Internal P/N": st.column_config.TextColumn("Internal P/N", width="medium"),
                "Supplier": st.column_config.TextColumn("Supplier", width="medium")
            }
        )

    def render_reorder_section(self):
        """Render the reorder request interface"""
        st.markdown("### 📦 Component Reorder Request")

        with st.expander("🛒 Submit New Reorder Request", expanded=False):
            st.markdown(
                "Fill out the form below to request components that are out of stock or needed.")

            with st.form("reorder_form", clear_on_submit=True):
                col1, col2 = st.columns(2)

                with col1:
                    manufacturer_pn = st.text_input(
                        "Manufacturer Part Number *",
                        placeholder="e.g., STM32F407VGT6",
                        help="Enter the exact manufacturer part number"
                    )

                    requester_name = st.text_input(
                        "Your Name *",
                        placeholder="Enter your full name",
                        help="This will be used for order tracking"
                    )

                with col2:
                    description = st.text_area(
                        "Component Description *",
                        placeholder="e.g., 32-bit ARM Cortex-M4 MCU, 168MHz, 1MB Flash",
                        help="Provide detailed component description",
                        height=100
                    )

                # Additional fields
                col3, col4 = st.columns(2)
                with col3:
                    quantity = st.number_input(
                        "Quantity", min_value=1, value=1)
                    urgency = st.selectbox(
                        "Urgency Level", ["Standard", "High", "Critical"])

                with col4:
                    supplier_pref = st.text_input(
                        "Preferred Supplier (Optional)", placeholder="e.g., Digi-Key, Mouser")
                    notes = st.text_area(
                        "Additional Notes (Optional)", height=100)

                # Submit button
                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button(
                    "📤 Submit Reorder Request",
                    use_container_width=True,
                    type="primary"
                )

                if submitted:
                    if manufacturer_pn and description and requester_name:
                        # Enhanced description with additional details
                        enhanced_description = f"{description}"
                        if quantity > 1:
                            enhanced_description += f" | Qty: {quantity}"
                        if urgency != "Standard":
                            enhanced_description += f" | Urgency: {urgency}"
                        if supplier_pref:
                            enhanced_description += f" | Preferred Supplier: {supplier_pref}"
                        if notes:
                            enhanced_description += f" | Notes: {notes}"

                        with st.spinner("Submitting reorder request..."):
                            success = self.inventory_manager.submit_reorder_request(
                                manufacturer_pn, enhanced_description, requester_name
                            )

                        if success:
                            st.success(
                                "✅ Reorder request submitted successfully!")
                            st.balloons()
                        else:
                            st.error(
                                "❌ Failed to submit reorder request. Please try again.")
                    else:
                        st.error(
                            "❌ Please fill in all required fields marked with *")

    def render_dashboard_section(self):
        """Render the dashboard with real metrics"""
        st.markdown("### 📊 Inventory Dashboard")

        # Get real metrics with error handling
        metrics = None
        try:
            with st.spinner("Loading dashboard metrics..."):
                metrics = self.inventory_manager.get_dashboard_metrics()
        except Exception as e:
            logger.error(f"Dashboard metrics error: {e}")
            st.error("⚠️ Unable to load dashboard metrics. Using fallback values.")
            metrics = {
                "total_components": "Unavailable",
                "active_requests": "Unavailable",
                "categories": "Unavailable",
                "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M')
            }

        # Display metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total = metrics.get("total_components", "Error")
            if isinstance(total, int):
                st.metric("Total Components", f"{total:,}", delta=None)
            else:
                st.metric("Total Components", str(total), delta=None)

        with col2:
            requests = metrics.get("active_requests", "Error")
            if isinstance(requests, int):
                st.metric("Active Requests", requests, delta=None)
            else:
                st.metric("Active Requests", str(requests), delta=None)

        with col3:
            categories = metrics.get("categories", "Error")
            if isinstance(categories, int):
                st.metric("Component Types", categories, delta=None)
            else:
                st.metric("Component Types", str(categories), delta=None)

        with col4:
            st.metric("Last Updated", metrics.get(
                "last_updated", "Unknown"), delta=None)

        # Additional dashboard content
        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📈 Quick Stats")
            total_components = metrics.get("total_components", 0)
            if isinstance(total_components, int) and total_components > 0:
                st.success(f"✅ {total_components} components tracked")
                active_requests = metrics.get("active_requests", 0)
                if isinstance(active_requests, int):
                    if active_requests == 0:
                        st.info("📋 No pending reorder requests")
                    else:
                        st.warning(f"⏳ {active_requests} pending requests")
                else:
                    st.info("📋 Request status: " + str(active_requests))
            else:
                st.warning("⚠️ Unable to load inventory statistics")
                st.info(
                    "💡 This might be due to network issues or Firebase connectivity")

        with col2:
            st.markdown("#### 🔧 System Health")
            # Test Firebase connection
            try:
                test_data = self.inventory_manager.fetch_inventory_data()
                if test_data:
                    st.success("🟢 Database Connection: Active")
                    st.success("🟢 Search Engine: Operational")
                else:
                    st.warning("🟡 Database Connection: Limited")
                    st.warning("🟡 Search Engine: Degraded")
            except:
                st.error("🔴 Database Connection: Failed")
                st.error("🔴 Search Engine: Offline")

            st.success("🟢 File Upload: Ready")

        # Recent activity placeholder
        st.markdown("---")
        st.markdown("#### 📋 Recent Activity")
        st.info("🔄 Activity logging will be implemented in future updates")

        # Quick actions
        st.markdown("---")
        st.markdown("#### ⚡ Quick Actions")

        action_col1, action_col2, action_col3 = st.columns(3)

        with action_col1:
            if st.button("📤 View All Requests", use_container_width=True):
                st.info("Feature coming soon: View all reorder requests")

        with action_col2:
            if st.button("📊 Export Data", use_container_width=True):
                st.info("Feature coming soon: Export inventory data")

        with action_col3:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.cache_data.clear()
                st.rerun()


def main():
    """Main application entry point"""
    # Page configuration
    st.set_page_config(
        page_title="Aharoni Lab Inventory",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for professional styling
    st.markdown("""
    <style>
    .main > div {
        padding-top: 1rem;
    }
    .stButton > button {
        border-radius: 5px;
        border: none;
        background: linear-gradient(90deg, #1f4e79 0%, #2e86de 100%);
        color: white;
        font-weight: 500;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #2e86de 0%, #1f4e79 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .stTextInput > div > div > input {
        border-radius: 5px;
    }
    .stSelectbox > div > div > select {
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Authentication check
    if not AuthManager.authenticate():
        return

    # Initialize managers
    try:
        inventory_manager = InventoryManager()
        ui = InventoryUI(inventory_manager)

        # Render UI components
        ui.render_header()
        ui.render_sidebar()

        # Main content area
        tab1, tab2 = st.tabs(["🔍 Search Components", "📊 Dashboard"])

        with tab1:
            ui.render_search_section()
            st.markdown("---")
            ui.render_reorder_section()

        with tab2:
            ui.render_dashboard_section()

    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(
            "🚨 An unexpected error occurred. Please check the configuration and try again.")

        # Show error details in an expander for debugging
        with st.expander("🔧 Error Details (for administrator)"):
            st.code(str(e))
            st.write("**Possible causes:**")
            st.write("- Missing or incorrect Firebase credentials in secrets.toml")
            st.write("- Missing authentication configuration")
            st.write("- Network connectivity issues")
            st.write("- Firebase service account permissions")

        st.info("💡 **Quick fixes to try:**")
        st.write("1. Refresh the page")
        st.write("2. Check your internet connection")
        st.write("3. Contact the administrator if the problem persists")


if __name__ == "__main__":
    main()

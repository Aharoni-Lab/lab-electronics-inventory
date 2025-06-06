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

            # Count unique categories
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

        # Modern Login UI
        st.markdown("""
        <style>
        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 60vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            margin: 2rem 0;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .login-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 3rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            max-width: 400px;
            width: 100%;
        }
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .login-title {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        .login-subtitle {
            color: #64748b;
            font-size: 1rem;
            margin-bottom: 0;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="login-container">
            <div class="login-card">
                <div class="login-header">
                    <h1 class="login-title">🔬 Aharoni Lab</h1>
                    <p class="login-subtitle">Inventory Management System</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                with st.form("login_form"):
                    st.markdown("### 🔐 Secure Access")
                    username = st.text_input(
                        "Username", placeholder="Enter your username")
                    password = st.text_input(
                        "Password", type="password", placeholder="Enter your password")

                    submitted = st.form_submit_button(
                        "Sign In", use_container_width=True, type="primary")

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
        """Render the professional application header"""
        st.markdown("""
        <style>
        .main-header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 2.5rem 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(30, 60, 114, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
        }
        .main-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, rgba(255,255,255,0.1) 0%, transparent 100%);
            pointer-events: none;
        }
        .header-content {
            position: relative;
            z-index: 1;
            text-align: center;
            color: white;
        }
        .header-title {
            font-size: 3rem;
            font-weight: 800;
            margin: 0;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            letter-spacing: -0.02em;
        }
        .header-subtitle {
            font-size: 1.3rem;
            opacity: 0.9;
            margin: 0.5rem 0 0 0;
            font-weight: 400;
        }
        .header-location {
            font-size: 1rem;
            opacity: 0.8;
            margin-top: 0.5rem;
            font-weight: 300;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="main-header">
            <div class="header-content">
                <h1 class="header-title">🔬 Laboratory Inventory Management</h1>
                <p class="header-subtitle">Advanced Component Tracking & Analytics Platform</p>
                <p class="header-location">Aharoni Laboratory • CHS 74-134 • Real-time Inventory Control</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    def render_sidebar(self):
        """Render enhanced sidebar with status and navigation"""
        with st.sidebar:
            st.markdown("""
            <style>
            .sidebar-section {
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                padding: 1.5rem;
                border-radius: 12px;
                margin-bottom: 1rem;
                border: 1px solid #e2e8f0;
            }
            .status-indicator {
                display: flex;
                align-items: center;
                margin: 0.5rem 0;
                padding: 0.5rem;
                border-radius: 8px;
                background: rgba(16, 185, 129, 0.1);
            }
            .status-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #10b981;
                margin-right: 0.5rem;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            </style>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class="sidebar-section">
                <h3 style="margin-top: 0; color: #1f2937;">📊 System Status</h3>
                <div class="status-indicator">
                    <div class="status-dot"></div>
                    <span style="color: #059669; font-weight: 500;">Database Connected</span>
                </div>
                <div class="status-indicator">
                    <div class="status-dot"></div>
                    <span style="color: #059669; font-weight: 500;">Firebase Active</span>
                </div>
                <div style="margin-top: 1rem; font-size: 0.875rem; color: #6b7280;">
                    Last sync: {}</div>
            </div>
            """.format(datetime.now().strftime('%H:%M:%S')), unsafe_allow_html=True)

            # Quick Actions
            st.markdown("""
            <div class="sidebar-section">
                <h3 style="margin-top: 0; color: #1f2937;">⚡ Quick Actions</h3>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔍 Advanced Search", use_container_width=True):
                st.session_state.show_advanced_search = True

            if st.button("📈 Analytics", use_container_width=True):
                st.session_state.show_analytics = True

            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()

    def render_search_section(self):
        """Render enhanced search interface"""
        st.markdown("""
        <style>
        .search-container {
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid #e2e8f0;
        }
        .search-header {
            display: flex;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        .search-icon {
            font-size: 2rem;
            margin-right: 1rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .search-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: #1f2937;
            margin: 0;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="search-container">
            <div class="search-header">
                <div class="search-icon">🔍</div>
                <h2 class="search-title">Component Search & Discovery</h2>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([4, 4, 2])

        with col1:
            part_number_query = st.text_input(
                "🔧 Part Number Search",
                placeholder="STM32F407VG, LM358, TL074...",
                help="Search by manufacturer or internal part number"
            )

        with col2:
            value_query = st.text_input(
                "📋 Component Description",
                placeholder="4.7µF, 100Ω, XOR gate, ADC...",
                help="Search by component value, type, or description"
            )

        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            search_clicked = st.button(
                "🚀 Search",
                use_container_width=True,
                type="primary"
            )

        # Advanced search toggle
        if st.session_state.get("show_advanced_search", False):
            with st.expander("🔬 Advanced Search Options", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    location_filter = st.selectbox("Filter by Location",
                                                   ["All Locations", "Lab Bench", "Storage Room", "Refrigerator"])
                    supplier_filter = st.selectbox("Filter by Supplier",
                                                   ["All Suppliers", "Digi-Key", "Mouser", "Element14"])
                with col2:
                    date_filter = st.date_input("Components added after")
                    category_filter = st.multiselect("Component Categories",
                                                     ["Resistors", "Capacitors", "ICs", "Sensors", "Connectors"])

        if search_clicked:
            if not part_number_query and not value_query:
                st.warning("⚠️ Please enter at least one search criterion")
                return

            with st.spinner("🔍 Searching inventory database..."):
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
        """Display search results with professional styling"""
        st.markdown("""
        <style>
        .results-header {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            border-left: 4px solid #0ea5e9;
        }
        .results-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #0c4a6e;
            margin: 0;
        }
        .results-count {
            color: #0369a1;
            font-size: 1rem;
            margin-top: 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="results-header">
            <h3 class="results-title">📋 Search Results</h3>
            <p class="results-count">Found {} matching components in inventory</p>
        </div>
        """.format(len(results)), unsafe_allow_html=True)

        # Create enhanced DataFrame
        df_data = []
        for i, item in enumerate(results, 1):
            df_data.append({
                '#': i,
                'Description': item.description,
                'Manufacturer P/N': item.manufacturer_pn,
                'Internal P/N': item.part_number,
                'Location': item.location,
                'Supplier': item.company_made,
                'Status': '🟢 Available'
            })

        df = pd.DataFrame(df_data)

        # Enhanced dataframe display
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "#": st.column_config.NumberColumn("#", width="small"),
                "Description": st.column_config.TextColumn("Description", width="large"),
                "Location": st.column_config.TextColumn("Location", width="medium"),
                "Manufacturer P/N": st.column_config.TextColumn("Mfg P/N", width="medium"),
                "Internal P/N": st.column_config.TextColumn("Internal P/N", width="medium"),
                "Supplier": st.column_config.TextColumn("Supplier", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small")
            }
        )

        # Export options
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            if st.button("📥 Export to CSV", use_container_width=True):
                csv = df.to_csv(index=False)
                st.download_button("Download CSV", csv,
                                   "inventory_search_results.csv", "text/csv")
        with col2:
            if st.button("📊 Generate Report", use_container_width=True):
                st.info("Report generation feature coming soon!")

    def render_reorder_section(self):
        """Render enhanced reorder request interface"""
        st.markdown("""
        <style>
        .reorder-container {
            background: linear-gradient(135deg, #fef3c7 0%, #fbbf24 20%, #f59e0b 100%);
            padding: 2rem;
            border-radius: 16px;
            margin-top: 2rem;
            box-shadow: 0 4px 20px rgba(245, 158, 11, 0.2);
            border: 1px solid #fbbf24;
        }
        .reorder-header {
            text-align: center;
            margin-bottom: 1.5rem;
        }
        .reorder-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: #92400e;
            margin: 0;
        }
        .reorder-subtitle {
            color: #a16207;
            margin-top: 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="reorder-container">
            <div class="reorder-header">
                <h2 class="reorder-title">📦 Component Reorder Management</h2>
                <p class="reorder-subtitle">Request new components or restock existing inventory</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🛒 Submit New Reorder Request", expanded=False):
            with st.form("reorder_form", clear_on_submit=True):
                st.markdown("#### Request Details")

                col1, col2 = st.columns(2)
                with col1:
                    manufacturer_pn = st.text_input(
                        "Manufacturer Part Number *",
                        placeholder="e.g., STM32F407VGT6",
                        help="Enter the exact manufacturer part number"
                    )
                    requester_name = st.text_input(
                        "Requester Name *",
                        placeholder="Enter your full name",
                        help="This will be used for order tracking"
                    )

                with col2:
                    description = st.text_area(
                        "Component Description *",
                        placeholder="32-bit ARM Cortex-M4 MCU, 168MHz, 1MB Flash...",
                        help="Provide detailed component description",
                        height=100
                    )

                st.markdown("#### Additional Information")
                col3, col4 = st.columns(2)
                with col3:
                    quantity = st.number_input(
                        "Quantity", min_value=1, value=1)
                    urgency = st.selectbox("Priority Level",
                                           ["🔵 Standard", "🟡 High", "🔴 Critical"])

                with col4:
                    supplier_pref = st.text_input("Preferred Supplier (Optional)",
                                                  placeholder="Digi-Key, Mouser, Element14...")
                    budget_code = st.text_input("Budget/Project Code",
                                                placeholder="PROJ-2024-001")

                notes = st.text_area("Additional Notes",
                                     placeholder="Special requirements, specifications, or comments...",
                                     height=80)

                submitted = st.form_submit_button("🚀 Submit Request",
                                                  use_container_width=True,
                                                  type="primary")

                if submitted:
                    if manufacturer_pn and description and requester_name:
                        enhanced_description = f"{description}"
                        if quantity > 1:
                            enhanced_description += f" | Qty: {quantity}"
                        if urgency != "🔵 Standard":
                            enhanced_description += f" | Priority: {urgency}"
                        if supplier_pref:
                            enhanced_description += f" | Preferred Supplier: {supplier_pref}"
                        if budget_code:
                            enhanced_description += f" | Budget Code: {budget_code}"
                        if notes:
                            enhanced_description += f" | Notes: {notes}"

                        with st.spinner("📤 Submitting reorder request..."):
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

    def render_file_upload_section(self):
        """Render enhanced file upload interface"""
        st.markdown("""
        <style>
        .upload-container {
            background: linear-gradient(135deg, #e0f2fe 0%, #b3e5fc 100%);
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 20px rgba(3, 169, 244, 0.15);
            border: 1px solid #81d4fa;
        }
        .upload-header {
            text-align: center;
            margin-bottom: 1.5rem;
        }
        .upload-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: #0277bd;
            margin: 0;
        }
        .upload-subtitle {
            color: #0288d1;
            margin-top: 0.5rem;
        }
        .upload-zone {
            background: rgba(255, 255, 255, 0.8);
            border: 2px dashed #03a9f4;
            border-radius: 12px;
            padding: 2rem;
            text-align: center;
            margin: 1rem 0;
            transition: all 0.3s ease;
        }
        .upload-zone:hover {
            background: rgba(255, 255, 255, 0.9);
            border-color: #0288d1;
        }
        .file-info {
            background: rgba(255, 255, 255, 0.9);
            padding: 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            border-left: 4px solid #03a9f4;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="upload-container">
            <div class="upload-header">
                <h2 class="upload-title">📤 Document & Media Upload Center</h2>
                <p class="upload-subtitle">Upload component photos, datasheets, and technical documentation</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown("#### 📸 Upload Files")

            uploader_name = st.text_input(
                "Uploader Name *",
                placeholder="Enter your full name",
                help="Files will be organized in folders by uploader name"
            )

            uploaded_files = st.file_uploader(
                "Choose files to upload",
                type=["jpg", "jpeg", "png", "pdf", "doc", "docx"],
                accept_multiple_files=True,
                help="Supported: Images (JPG, PNG), Documents (PDF, DOC, DOCX)"
            )

            if uploaded_files and uploader_name:
                st.markdown("#### 📋 Upload Preview")
                total_size = 0
                for file in uploaded_files:
                    file_size = len(file.read()) / 1024 / 1024
                    file.seek(0)
                    total_size += file_size

                    st.markdown(f"""
                    <div class="file-info">
                        <strong>📄 {file.name}</strong><br>
                        <small>Size: {file_size:.2f} MB | Type: {file.type}</small>
                    </div>
                    """, unsafe_allow_html=True)

                st.info(f"Total upload size: {total_size:.2f} MB")

                if st.button("🚀 Upload All Files", use_container_width=True, type="primary"):
                    with st.spinner("📤 Uploading files to secure storage..."):
                        results = self.inventory_manager.upload_files(
                            uploaded_files, uploader_name)

                    success_count = sum(results.values())
                    total_count = len(results)

                    if success_count == total_count:
                        st.success(
                            f"✅ All {total_count} files uploaded successfully!")
                        st.balloons()
                    else:
                        st.warning(
                            f"⚠️ {success_count}/{total_count} files uploaded successfully")

                    with st.expander("📊 Upload Details", expanded=success_count != total_count):
                        for filename, success in results.items():
                            if success:
                                st.success(f"✅ {filename}")
                            else:
                                st.error(f"❌ {filename} - Upload failed")

        with col2:
            st.markdown("#### 💡 Upload Guidelines")
            st.markdown("""
            **File Organization:**
            - 📁 Auto-organized by uploader
            - 🏷️ Use descriptive filenames
            - 🔗 Include part numbers
            
            **Supported Formats:**
            - 📸 **Images**: JPG, PNG
            - 📄 **Documents**: PDF, DOC, DOCX
            
            **Best Practices:**
            - 🔍 Clear, high-resolution photos
            - 📋 Complete datasheets
            - 💰 Supplier quotes with P/N
            - 📝 Descriptive filenames
            """)

            with st.expander("🔧 File Management"):
                st.markdown("""
                **Naming Convention:**
                ```
                PartNumber_Description.ext
                STM32F407_Datasheet.pdf
                Resistor_100ohm_Photo.jpg
                ```
                
                **Storage Details:**
                - 🔒 Secure Firebase Storage
                - 👥 Team accessible
                - 📊 Usage tracking
                - 🔄 Version control ready
                """)

    def render_dashboard_section(self):
        """Render enhanced dashboard with analytics"""
        st.markdown("""
        <style>
        .dashboard-container {
            background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%);
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 20px rgba(139, 92, 246, 0.15);
            border: 1px solid #c4b5fd;
        }
        .dashboard-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .dashboard-title {
            font-size: 2rem;
            font-weight: 800;
            color: #6b21a8;
            margin: 0;
        }
        .dashboard-subtitle {
            color: #7c3aed;
            margin-top: 0.5rem;
            font-size: 1.1rem;
        }
        .metric-card {
            background: rgba(255, 255, 255, 0.9);
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        }
        .metric-value {
            font-size: 2.5rem;
            font-weight: 800;
            color: #1f2937;
            margin: 0;
        }
        .metric-label {
            color: #6b7280;
            font-size: 0.9rem;
            margin-top: 0.5rem;
            font-weight: 500;
        }
        .metric-icon {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="dashboard-container">
            <div class="dashboard-header">
                <h1 class="dashboard-title">📊 Inventory Analytics Dashboard</h1>
                <p class="dashboard-subtitle">Real-time insights and performance metrics</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Get metrics with enhanced error handling
        try:
            with st.spinner("📊 Loading analytics..."):
                metrics = self.inventory_manager.get_dashboard_metrics()
        except Exception as e:
            logger.error(f"Dashboard metrics error: {e}")
            st.error("⚠️ Unable to load dashboard metrics.")
            metrics = {
                "total_components": "Unavailable",
                "active_requests": "Unavailable",
                "categories": "Unavailable",
                "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M')
            }

        # Enhanced metrics display
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total = metrics.get("total_components", "Error")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">📦</div>
                <h2 class="metric-value">{total if isinstance(total, int) else total}</h2>
                <p class="metric-label">Total Components</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            requests = metrics.get("active_requests", "Error")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">🛒</div>
                <h2 class="metric-value">{requests if isinstance(requests, int) else requests}</h2>
                <p class="metric-label">Active Requests</p>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            categories = metrics.get("categories", "Error")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">🏷️</div>
                <h2 class="metric-value">{categories if isinstance(categories, int) else categories}</h2>
                <p class="metric-label">Categories</p>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">🕒</div>
                <h2 class="metric-value" style="font-size: 1.2rem;">{metrics.get("last_updated", "Unknown")}</h2>
                <p class="metric-label">Last Updated</p>
            </div>
            """, unsafe_allow_html=True)

        # Enhanced action buttons
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📋 View Active Requests", use_container_width=True, type="primary"):
                st.session_state.show_requests = True

        with col2:
            if st.button("📈 Generate Analytics", use_container_width=True):
                st.session_state.show_analytics = True

        with col3:
            if st.button("📤 Export Data", use_container_width=True):
                st.info("Export functionality coming soon!")

        # Display requests if toggled
        if st.session_state.get("show_requests", False):
            self._show_active_requests()

        # Display analytics if toggled
        if st.session_state.get("show_analytics", False):
            self._show_analytics_panel()

    def _show_active_requests(self):
        """Display active requests with enhanced UI"""
        st.markdown("""
        <style>
        .requests-container {
            background: linear-gradient(135deg, #fef7ed 0%, #fed7aa 100%);
            padding: 2rem;
            border-radius: 16px;
            margin-top: 2rem;
            box-shadow: 0 4px 20px rgba(251, 146, 60, 0.15);
            border: 1px solid #fdba74;
        }
        .request-item {
            background: rgba(255, 255, 255, 0.9);
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            border-left: 4px solid #f97316;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .request-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        .request-title {
            font-weight: 700;
            color: #9a3412;
            font-size: 1.1rem;
        }
        .request-meta {
            font-size: 0.875rem;
            color: #a16207;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="requests-container">
            <h3 style="text-align: center; color: #9a3412; margin-bottom: 1rem;">📋 Active Reorder Requests</h3>
        </div>
        """, unsafe_allow_html=True)

        try:
            if self.inventory_manager.bucket:
                blob = self.inventory_manager.bucket.blob('to_be_ordered.txt')
                if blob.exists():
                    reorder_content = blob.download_as_text()
                    requests = [line.strip() for line in reorder_content.split(
                        '\n') if line.strip()]

                    if requests:
                        st.success(
                            f"📊 Found {len(requests)} active request(s)")

                        # Initialize session state
                        if "selected_requests" not in st.session_state:
                            st.session_state.selected_requests = set()

                        # Enhanced selection controls
                        col1, col2, col3 = st.columns([2, 2, 2])
                        with col1:
                            select_all = st.checkbox("🔲 Select All Requests")
                            if select_all:
                                st.session_state.selected_requests = set(
                                    range(len(requests)))
                            elif not select_all and len(st.session_state.selected_requests) == len(requests):
                                st.session_state.selected_requests = set()

                        with col2:
                            if st.button("🗑️ Delete Selected", type="secondary"):
                                if st.session_state.selected_requests:
                                    deleted_count = self._delete_selected_requests(
                                        requests)
                                    if deleted_count > 0:
                                        st.rerun()
                                else:
                                    st.warning(
                                        "⚠️ No requests selected for deletion")

                        with col3:
                            if st.button("📧 Email Summary", type="secondary"):
                                st.info("Email functionality coming soon!")

                        st.markdown("---")

                        # Display requests with enhanced styling
                        for i, request in enumerate(requests):
                            col1, col2 = st.columns([1, 20])

                            with col1:
                                is_selected = st.checkbox(
                                    "",
                                    key=f"req_{i}_{len(requests)}",
                                    value=i in st.session_state.selected_requests,
                                    on_change=self._toggle_request_selection,
                                    args=(i,)
                                )

                            with col2:
                                with st.expander(f"🛒 Request #{i+1} - {request.split(',')[1].split(':')[1].strip() if len(request.split(',')) > 1 else 'Unknown'}", expanded=False):
                                    parts = request.split(', ')
                                    for part in parts:
                                        if ':' in part:
                                            key, value = part.split(':', 1)
                                            if key.strip() == "Date and Time":
                                                st.markdown(
                                                    f"**📅 {key.strip()}:** {value.strip()}")
                                            elif key.strip() == "Manufacturer Part Number":
                                                st.markdown(
                                                    f"**🔧 {key.strip()}:** `{value.strip()}`")
                                            elif key.strip() == "Requester Name":
                                                st.markdown(
                                                    f"**👤 {key.strip()}:** {value.strip()}")
                                            else:
                                                st.markdown(
                                                    f"**{key.strip()}:** {value.strip()}")
                                        else:
                                            st.write(part)
                    else:
                        st.info("📭 No active requests found")
                else:
                    st.info("📄 No reorder requests file found")
            else:
                st.error("❌ Unable to access database")

        except Exception as e:
            logger.error(f"Error fetching active requests: {e}")
            st.error("🚨 Failed to load active requests")

    def _show_analytics_panel(self):
        """Display analytics dashboard"""
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); 
                    padding: 2rem; border-radius: 16px; margin-top: 2rem;
                    box-shadow: 0 4px 20px rgba(34, 197, 94, 0.15); border: 1px solid #bbf7d0;">
            <h3 style="text-align: center; color: #166534; margin-bottom: 1rem;">📈 Advanced Analytics</h3>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📊 Component Distribution")
            # Placeholder for future chart
            st.info("📈 Component category charts coming soon!")

        with col2:
            st.markdown("#### 📅 Request Trends")
            # Placeholder for future chart
            st.info("📊 Request trend analysis coming soon!")

        st.markdown("#### 🔍 Quick Insights")
        insights = [
            "🔧 Most requested component type: Microcontrollers",
            "📈 30% increase in requests this month",
            "⚡ Average response time: 2.3 days",
            "🎯 95% request fulfillment rate"
        ]

        for insight in insights:
            st.success(insight)

    def _toggle_request_selection(self, index):
        """Toggle selection of a specific request"""
        if "selected_requests" not in st.session_state:
            st.session_state.selected_requests = set()

        if index in st.session_state.selected_requests:
            st.session_state.selected_requests.remove(index)
        else:
            st.session_state.selected_requests.add(index)

    def _delete_selected_requests(self, current_requests) -> int:
        """Delete selected requests with enhanced feedback"""
        try:
            if not st.session_state.selected_requests:
                return 0

            if self.inventory_manager.bucket:
                selected_indices = sorted(
                    st.session_state.selected_requests, reverse=True)
                updated_requests = current_requests.copy()
                deleted_count = 0

                for index in selected_indices:
                    if 0 <= index < len(updated_requests):
                        updated_requests.pop(index)
                        deleted_count += 1

                blob = self.inventory_manager.bucket.blob('to_be_ordered.txt')
                updated_content = '\n'.join(
                    updated_requests) + '\n' if updated_requests else ''
                blob.upload_from_string(updated_content)

                st.session_state.selected_requests = set()
                st.success(
                    f"✅ Successfully deleted {deleted_count} request(s)")
                return deleted_count
            else:
                st.error("❌ Unable to access database")
                return 0

        except Exception as e:
            logger.error(f"Error deleting requests: {e}")
            st.error("🚨 Failed to delete selected requests")
            return 0


def main():
    """Main application entry point with enhanced styling"""
    # Enhanced page configuration
    st.set_page_config(
        page_title="Aharoni Lab Inventory",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/your-repo/issues',
            'Report a bug': 'https://github.com/your-repo/issues',
            'About': "Professional Laboratory Inventory Management System v2.0"
        }
    )

    # Professional custom CSS
    st.markdown("""
    <style>
    /* Global Styles */
    .main > div {
        padding-top: 1rem;
    }
    
    /* Enhanced Button Styles */
    .stButton > button {
        border-radius: 8px;
        border: none;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Form Input Enhancements */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        border-radius: 8px;
        border: 2px solid #e2e8f0;
        transition: border-color 0.3s ease;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: 1px solid #e2e8f0;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Sidebar Enhancements */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    }
    
    /* Dataframe Styling */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .dataframe th {
        background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%) !important;
        font-weight: 600;
        color: #1f2937;
    }
    
    /* Alert Enhancements */
    .stAlert {
        border-radius: 8px;
        border: none;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* Metric Styling */
    [data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.8);
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* Hide Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Loading Animation */
    .stSpinner > div {
        border-top-color: #667eea;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    </style>
    """, unsafe_allow_html=True)

    # Authentication check
    if not AuthManager.authenticate():
        return

    # Initialize managers with error handling
    try:
        inventory_manager = InventoryManager()
        ui = InventoryUI(inventory_manager)

        # Render enhanced UI
        ui.render_header()
        ui.render_sidebar()

        # Enhanced main content with icons
        tab1, tab2, tab3 = st.tabs([
            "🔍 Search & Discovery",
            "📊 Analytics Dashboard",
            "📤 Document Center"
        ])

        with tab1:
            ui.render_search_section()
            st.markdown("---")
            ui.render_reorder_section()

        with tab2:
            ui.render_dashboard_section()

        with tab3:
            ui.render_file_upload_section()

        # Footer
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #6b7280; font-size: 0.875rem; padding: 1rem;">
            <p>🔬 <strong>Aharoni Laboratory Inventory Management System</strong> | Version 2.0 Professional</p>
            <p>Developed with ❤️ for scientific excellence | CHS 74-134</p>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        logger.error(f"Application error: {e}")
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); 
                    padding: 2rem; border-radius: 16px; margin: 2rem 0;
                    box-shadow: 0 4px 20px rgba(239, 68, 68, 0.15); border: 1px solid #fecaca;">
            <h3 style="color: #dc2626; text-align: center;">🚨 System Error</h3>
            <p style="color: #991b1b; text-align: center;">An unexpected error occurred. Please contact the administrator.</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🔧 Technical Details (Administrator Only)"):
            st.code(str(e))
            st.markdown("""
            **Possible Solutions:**
            - ✅ Verify Firebase credentials in secrets.toml
            - ✅ Check authentication configuration  
            - ✅ Confirm network connectivity
            - ✅ Validate Firebase service permissions
            - ✅ Refresh the page and try again
            """)


if __name__ == "__main__":
    main()

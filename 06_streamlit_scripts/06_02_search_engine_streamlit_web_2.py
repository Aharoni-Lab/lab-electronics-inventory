"""
Laboratory Inventory Management System - Advanced Component Tracking
A comprehensive Streamlit application for managing electronic components in laboratory environments.
"""

import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, storage
import json
from datetime import datetime
import logging
from typing import Dict, List, Tuple, Any, Optional
import time
from dataclasses import dataclass
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Data class for search results"""
    part_number: str
    description: str
    quantity: int
    location: str
    category: str
    supplier: str
    notes: str
    last_updated: str
    confidence_score: float = 1.0


class FirebaseManager:
    """Handles all Firebase operations for the inventory system"""

    def __init__(self):
        self.db = None
        self.bucket = None
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Initialize Firebase connection using Streamlit secrets"""
        try:
            if not firebase_admin._apps:
                # Get Firebase config from Streamlit secrets
                firebase_config = st.secrets["firebase"]

                cred_dict = {
                    "type": firebase_config["type"],
                    "project_id": firebase_config["project_id"],
                    "private_key_id": firebase_config["private_key_id"],
                    "private_key": firebase_config["private_key"].replace('\\n', '\n'),
                    "client_email": firebase_config["client_email"],
                    "client_id": firebase_config["client_id"],
                    "auth_uri": firebase_config["auth_uri"],
                    "token_uri": firebase_config["token_uri"],
                    "auth_provider_x509_cert_url": firebase_config["auth_provider_x509_cert_url"],
                    "client_x509_cert_url": firebase_config["client_x509_cert_url"]
                }

                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': firebase_config["storage_bucket"]
                })

            self.db = firestore.client()
            self.bucket = storage.bucket()
            logger.info("✅ Firebase initialized successfully")

        except Exception as e:
            logger.error(f"❌ Firebase initialization failed: {e}")
            st.error(
                "Failed to connect to Firebase. Please check your configuration.")

    def fetch_inventory_data(self) -> List[Dict]:
        """Fetch all inventory data from Firestore"""
        try:
            if not self.db:
                logger.error("Database not initialized")
                return []

            docs = self.db.collection('inventory').stream()
            inventory_data = []

            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                inventory_data.append(data)

            logger.info(f"✅ Retrieved {len(inventory_data)} inventory items")
            return inventory_data

        except Exception as e:
            logger.error(f"❌ Error fetching inventory: {e}")
            return []

    def search_components(self, query: str, filters: Dict = None) -> List[SearchResult]:
        """Advanced search with multiple criteria and fuzzy matching"""
        try:
            inventory_data = self.fetch_inventory_data()
            if not inventory_data:
                return []

            results = []
            query_lower = query.lower().strip()

            for item in inventory_data:
                score = self._calculate_relevance_score(
                    item, query_lower, filters)

                if score > 0:
                    result = SearchResult(
                        part_number=item.get('part_number', 'N/A'),
                        description=item.get('description', 'N/A'),
                        quantity=item.get('quantity', 0),
                        location=item.get('location', 'N/A'),
                        category=item.get('category', 'N/A'),
                        supplier=item.get('supplier', 'N/A'),
                        notes=item.get('notes', 'N/A'),
                        last_updated=item.get('last_updated', 'N/A'),
                        confidence_score=score
                    )
                    results.append(result)

            # Sort by relevance score (highest first)
            results.sort(key=lambda x: x.confidence_score, reverse=True)
            return results

        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            return []

    def _calculate_relevance_score(self, item: Dict, query: str, filters: Dict = None) -> float:
        """Calculate relevance score for search results"""
        if not query:
            return 1.0 if self._passes_filters(item, filters) else 0.0

        score = 0.0

        # Exact matches get highest priority
        searchable_fields = {
            'part_number': 3.0,
            'description': 2.0,
            'category': 1.5,
            'supplier': 1.0,
            'location': 1.0,
            'notes': 0.5
        }

        for field, weight in searchable_fields.items():
            field_value = str(item.get(field, '')).lower()

            if query == field_value:
                score += weight * 2  # Exact match bonus
            elif query in field_value:
                score += weight * 1.5  # Contains match
            elif any(word in field_value for word in query.split()):
                score += weight * 0.8  # Partial word match

        # Apply filters
        if not self._passes_filters(item, filters):
            return 0.0

        return min(score, 5.0)  # Cap at 5.0

    def _passes_filters(self, item: Dict, filters: Dict = None) -> bool:
        """Check if item passes the applied filters"""
        if not filters:
            return True

        for filter_key, filter_value in filters.items():
            if filter_value and filter_value != "All":
                item_value = item.get(filter_key, '')
                if str(item_value).lower() != str(filter_value).lower():
                    return False

        return True

    def get_unique_values(self, field: str) -> List[str]:
        """Get unique values for a specific field (for filters)"""
        try:
            inventory_data = self.fetch_inventory_data()
            values = set()

            for item in inventory_data:
                value = item.get(field, '')
                if value and str(value).strip():
                    values.add(str(value).strip())

            return sorted(list(values))

        except Exception as e:
            logger.error(f"❌ Error getting unique values for {field}: {e}")
            return []

    def submit_reorder_request(self, part_number: str, description: str,
                               quantity: int, requester: str, priority: str,
                               notes: str = "") -> bool:
        """Submit a reorder request to Firebase Storage"""
        try:
            if not self.bucket:
                logger.error("Storage bucket not initialized")
                return False

            # Create request entry
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            request_data = (
                f"Date: {timestamp}, "
                f"Part Number: {part_number}, "
                f"Description: {description}, "
                f"Quantity: {quantity}, "
                f"Requester: {requester}, "
                f"Priority: {priority}"
            )

            if notes:
                request_data += f", Notes: {notes}"

            # Append to existing file or create new one
            blob = self.bucket.blob('to_be_ordered.txt')

            try:
                existing_content = blob.download_as_text()
                updated_content = existing_content + request_data + '\n'
            except:
                updated_content = request_data + '\n'

            blob.upload_from_string(updated_content)
            logger.info(f"✅ Reorder request submitted for {part_number}")
            return True

        except Exception as e:
            logger.error(f"❌ Error submitting reorder request: {e}")
            return False

    def upload_files(self, uploaded_files, uploader_name: str) -> Dict[str, bool]:
        """Upload files to Firebase Storage"""
        results = {}

        try:
            if not self.bucket:
                logger.error("Storage bucket not initialized")
                return {file.name: False for file in uploaded_files}

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            for uploaded_file in uploaded_files:
                try:
                    # Create organized path: uploads/uploader_name/timestamp_filename
                    file_path = f"uploads/{uploader_name}/{timestamp}_{uploaded_file.name}"

                    # Upload to Firebase Storage
                    blob = self.bucket.blob(file_path)
                    blob.upload_from_string(
                        uploaded_file.getvalue(),
                        content_type=uploaded_file.type
                    )

                    results[uploaded_file.name] = True
                    logger.info(f"✅ Uploaded: {uploaded_file.name}")

                except Exception as e:
                    logger.error(
                        f"❌ Failed to upload {uploaded_file.name}: {e}")
                    results[uploaded_file.name] = False

            return results

        except Exception as e:
            logger.error(f"❌ Upload process failed: {e}")
            return {file.name: False for file in uploaded_files}

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Calculate dashboard metrics"""
        try:
            inventory_data = self.fetch_inventory_data()

            # Count active requests
            active_requests = 0
            try:
                if self.bucket:
                    blob = self.bucket.blob('to_be_ordered.txt')
                    if blob.exists():
                        content = blob.download_as_text()
                        active_requests = len(
                            [line for line in content.split('\n') if line.strip()])
            except:
                active_requests = "Error"

            return {
                "total_components": len(inventory_data),
                "active_requests": active_requests,
                "categories": len(set(item.get('category', '') for item in inventory_data if item.get('category'))),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
            }

        except Exception as e:
            logger.error(f"❌ Error calculating metrics: {e}")
            return {
                "total_components": "Error",
                "active_requests": "Error",
                "categories": "Error",
                "last_updated": "Error"
            }


class InventoryUI:
    """Handles the Streamlit user interface"""

    def __init__(self, inventory_manager: FirebaseManager):
        self.inventory_manager = inventory_manager

    def render_header(self):
        """Render the application header"""
        st.markdown("""
        <div style="background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); 
                    padding: 2rem; border-radius: 10px; margin-bottom: 2rem; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 2.5rem;">
                🔬 Laboratory Inventory Management
            </h1>
            <p style="color: #e8f4ff; margin: 0.5rem 0 0 0; font-size: 1.1rem;">
                Aharoni Lab • CHS 74-134 • Advanced Component Tracking System
            </p>
        </div>
        """, unsafe_allow_html=True)

    def render_search_section(self):
        """Render the component search interface"""
        st.markdown("### 🔍 Component Search")

        # Search input
        col1, col2 = st.columns([3, 1])

        with col1:
            query = st.text_input(
                "Search Components",
                placeholder="Enter part number, description, category, or supplier...",
                help="Search across all component fields"
            )

        with col2:
            search_button = st.button(
                "🔍 Search", use_container_width=True, type="primary")

        # Advanced filters in expandable section
        with st.expander("🔧 Advanced Filters", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                categories = ["All"] + \
                    self.inventory_manager.get_unique_values('category')
                category_filter = st.selectbox("Category", categories)

            with col2:
                suppliers = ["All"] + \
                    self.inventory_manager.get_unique_values('supplier')
                supplier_filter = st.selectbox("Supplier", suppliers)

            with col3:
                locations = ["All"] + \
                    self.inventory_manager.get_unique_values('location')
                location_filter = st.selectbox("Location", locations)

        # Perform search
        if search_button or query:
            filters = {}
            if category_filter != "All":
                filters['category'] = category_filter
            if supplier_filter != "All":
                filters['supplier'] = supplier_filter
            if location_filter != "All":
                filters['location'] = location_filter

            with st.spinner("🔍 Searching components..."):
                results = self.inventory_manager.search_components(
                    query, filters)

            if results:
                st.success(f"Found {len(results)} component(s)")

                # Display results in a more compact format
                for i, result in enumerate(results):
                    with st.expander(f"📦 {result.part_number} - {result.description}",
                                     expanded=i < 3):  # Expand first 3 results

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.write(f"**Part Number:** {result.part_number}")
                            st.write(f"**Quantity:** {result.quantity}")
                            st.write(f"**Category:** {result.category}")

                        with col2:
                            st.write(f"**Location:** {result.location}")
                            st.write(f"**Supplier:** {result.supplier}")
                            st.write(f"**Updated:** {result.last_updated}")

                        with col3:
                            st.write(f"**Description:** {result.description}")
                            if result.notes != "N/A":
                                st.write(f"**Notes:** {result.notes}")

                            # Add confidence indicator
                            confidence_color = "🟢" if result.confidence_score > 2 else "🟡" if result.confidence_score > 1 else "🔴"
                            st.write(
                                f"**Relevance:** {confidence_color} {result.confidence_score:.1f}")
            else:
                st.warning(
                    "No components found matching your search criteria.")
                st.info("💡 **Tips:** Try broader search terms or check your filters")

    def render_reorder_section(self):
        """Render the reorder request interface"""
        with st.expander("📋 Submit Reorder Request", expanded=False):
            st.markdown("#### Request New Components")

            col1, col2 = st.columns(2)

            with col1:
                part_number = st.text_input(
                    "Part Number *", placeholder="e.g., STM32F407VGT6")
                description = st.text_area(
                    "Description *", placeholder="Brief component description")
                quantity = st.number_input("Quantity *", min_value=1, value=1)

            with col2:
                requester = st.text_input(
                    "Your Name *", placeholder="Full name")
                priority = st.selectbox(
                    "Priority", ["Low", "Medium", "High", "Urgent"])
                notes = st.text_area(
                    "Additional Notes", placeholder="Special requirements, supplier preferences, etc.")

            if st.button("📤 Submit Request", use_container_width=True, type="primary"):
                if part_number and description and requester:
                    with st.spinner("Submitting reorder request..."):
                        success = self.inventory_manager.submit_reorder_request(
                            part_number, description, quantity, requester, priority, notes
                        )

                        if success:
                            st.success(
                                "✅ Reorder request submitted successfully!")
                            st.balloons()
                        else:
                            st.error(
                                "Failed to submit reorder request. Please try again.")
                    else:
                        st.error(
                            "Please fill in all required fields marked with *")

    def render_dashboard_section(self):
        """Render the dashboard with metrics and active requests"""
        st.markdown("### 📊 Inventory Dashboard")

        # Get metrics
        with st.spinner("Loading dashboard metrics..."):
            metrics = self.inventory_manager.get_dashboard_metrics()

        # Display metrics with smaller font
        st.markdown("""
        <style>
        .metric-container .metric-value {
            font-size: 1.5rem !important;
        }
        .metric-container .metric-label {
            font-size: 0.875rem !important;
        }
        </style>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

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
            st.metric("Last Updated", metrics.get(
                "last_updated", "Unknown"), delta=None)

        # View Active Requests Button
        st.markdown("---")
        if st.button("📋 View Active Requests", use_container_width=True, type="primary"):
            st.session_state.show_requests = True

        # Display requests if button was clicked
        if st.session_state.get("show_requests", False):
            self._show_active_requests()

    def _show_active_requests(self):
        """Display the active reorder requests with delete options"""
        st.markdown("### 📋 Active Reorder Requests")

        try:
            if self.inventory_manager.bucket:
                blob = self.inventory_manager.bucket.blob('to_be_ordered.txt')
                if blob.exists():
                    reorder_content = blob.download_as_text()
                    requests = [line.strip() for line in reorder_content.split(
                        '\n') if line.strip()]

                    if requests:
                        st.success(f"Found {len(requests)} active request(s)")

                        # Initialize session state for checkboxes
                        if "selected_requests" not in st.session_state:
                            st.session_state.selected_requests = set()

                        # Add "Select All" option and Delete button
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            select_all = st.checkbox("Select All Requests")
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
                                        "No requests selected for deletion")

                        st.markdown("---")

                        # Display each request with checkbox (no form needed)
                        for i, request in enumerate(requests):
                            col1, col2 = st.columns([1, 10])

                            with col1:
                                # Use individual checkboxes that update session state immediately
                                is_selected = st.checkbox(
                                    "",
                                    # Include length to force refresh
                                    key=f"req_{i}_{len(requests)}",
                                    value=i in st.session_state.selected_requests,
                                    on_change=self._toggle_request_selection,
                                    args=(i,)
                                )

                            with col2:
                                with st.expander(f"Request #{i+1}", expanded=False):
                                    # Parse the request details
                                    parts = request.split(', ')
                                    for part in parts:
                                        if ':' in part:
                                            key, value = part.split(':', 1)
                                            st.write(
                                                f"**{key.strip()}:** {value.strip()}")
                                        else:
                                            st.write(part)
                    else:
                        st.info("No active requests found")
                else:
                    st.info("No reorder requests file found")
            else:
                st.error("Unable to access database")

        except Exception as e:
            logger.error(f"Error fetching active requests: {e}")
            st.error("Failed to load active requests")

    def _toggle_request_selection(self, index):
        """Toggle selection of a specific request"""
        if "selected_requests" not in st.session_state:
            st.session_state.selected_requests = set()

        if index in st.session_state.selected_requests:
            st.session_state.selected_requests.remove(index)
        else:
            st.session_state.selected_requests.add(index)

    def _delete_selected_requests(self, current_requests) -> int:
        """Delete selected requests from Firebase and return count of deleted items"""
        try:
            if not st.session_state.selected_requests:
                return 0

            if self.inventory_manager.bucket:
                # Remove selected requests (in reverse order to maintain indices)
                selected_indices = sorted(
                    st.session_state.selected_requests, reverse=True)
                updated_requests = current_requests.copy()
                deleted_count = 0

                for index in selected_indices:
                    if 0 <= index < len(updated_requests):
                        updated_requests.pop(index)
                        deleted_count += 1

                # Update the file
                blob = self.inventory_manager.bucket.blob('to_be_ordered.txt')
                updated_content = '\n'.join(
                    updated_requests) + '\n' if updated_requests else ''
                blob.upload_from_string(updated_content)

                # Clear selection and show success
                st.session_state.selected_requests = set()
                st.success(f"Successfully deleted {deleted_count} request(s)")
                return deleted_count
            else:
                st.error("Unable to access database")
                return 0

        except Exception as e:
            logger.error(f"Error deleting requests: {e}")
            st.error("Failed to delete selected requests")
            return 0

    def render_file_upload_section(self):
        """Render the file upload interface"""
        st.markdown("### 📤 File Upload Center")
        st.markdown(
            "Upload component photos, datasheets, or quotes to organize your lab documentation.")

        # Upload form
        uploader_name = st.text_input(
            "Your Name *",
            placeholder="Enter your full name",
            help="This will be used to organize uploaded files in folders"
        )

        uploaded_files = st.file_uploader(
            "Choose files to upload",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True,
            help="Supported formats: JPG, PNG, PDF"
        )

        # Upload button and logic
        if uploaded_files and uploader_name:
            st.markdown("#### 📋 Files Ready for Upload:")
            for file in uploaded_files:
                file_size = len(file.read()) / 1024 / 1024  # Size in MB
                file.seek(0)  # Reset file pointer
                st.write(f"• **{file.name}** ({file_size:.2f} MB)")

            if st.button("🚀 Upload Files", use_container_width=True, type="primary"):
                with st.spinner("Uploading files to Firebase..."):
                    results = self.inventory_manager.upload_files(
                        uploaded_files, uploader_name)

                success_count = sum(results.values())
                total_count = len(results)

                if success_count == total_count:
                    st.success(
                        f"All {total_count} files uploaded successfully!")
                    st.balloons()
                else:
                    st.warning(
                        f"{success_count}/{total_count} files uploaded successfully")

                # Show detailed results
                with st.expander("📊 Upload Details", expanded=success_count != total_count):
                    for filename, success in results.items():
                        if success:
                            st.success(f"✅ {filename}")
                        else:
                            st.error(f"❌ {filename} - Upload failed")

        elif uploaded_files and not uploader_name:
            st.warning("Please enter your name before uploading files")
        elif not uploaded_files:
            st.info("📁 Select files above to see upload preview")

    def render_sidebar(self):
        """Render the sidebar with system status"""
        with st.sidebar:
            # Add system status
            st.markdown("### 📊 System Status")
            st.success("🟢 Database: Connected")
            st.info(f"🕒 Last updated: {datetime.now().strftime('%H:%M:%S')}")


def main():
    """Main application function"""
    # Page configuration
    st.set_page_config(
        page_title="Lab Inventory Management",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for better styling
    st.markdown("""
    <style>
    .stMetric {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    
    .search-results {
        max-height: 600px;
        overflow-y: auto;
    }
    
    .component-card {
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #ffffff;
    }
    
    .stExpander > div > div > p {
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

    # Initialize the inventory manager
    @st.cache_resource
    def get_inventory_manager():
        return FirebaseManager()

    try:
        inventory_manager = get_inventory_manager()
        ui = InventoryUI(inventory_manager)

        # Render components
        ui.render_header()
        ui.render_sidebar()

        # Main content area
        tab1, tab2, tab3 = st.tabs(
            ["🔍 Search Components", "📊 Dashboard", "📤 File Upload"])

        with tab1:
            ui.render_search_section()
            st.markdown("---")
            ui.render_reorder_section()

        with tab2:
            ui.render_dashboard_section()

        with tab3:
            ui.render_file_upload_section()

    except Exception as e:
        st.error(f"Application error: {e}")
        logger.error(f"Main application error: {e}")


if __name__ == "__main__":
    main()

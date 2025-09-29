import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
from typing import Dict, Any, List, Optional
import re

# Backend API configuration
API_BASE_URL = "http://localhost:8000"  # Update this to your FastAPI server URL

def call_backend_api(query: str, tab: str, language: str = "english") -> Dict[str, Any]:
    """Call the FastAPI backend"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/query",
            json={
                "tab": tab,
                "query": query,
                "language": language
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API Error: {response.status_code} - {response.text}"}
    
    except requests.exceptions.RequestException as e:
        return {"error": f"Connection error: {str(e)}"}

def load_csv_from_url(csv_url: str) -> Optional[pd.DataFrame]:
    """Load CSV data from local file path"""
    try:
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {str(e)}")
        return None

def is_drift_query(query: str) -> bool:
    """Check if the query is about drift/trajectory"""
    drift_keywords = ['drift', 'trajectory', 'path', 'track', 'movement', 'route', 'journey', 'travel']
    return any(keyword in query.lower() for keyword in drift_keywords)

def has_geo_columns(df: pd.DataFrame) -> bool:
    """Check if DataFrame has geographic columns for drift plotting"""
    lat_cols = ['latitude', 'lat', 'Latitude', 'LAT', 'LATITUDE']
    lon_cols = ['longitude', 'lon', 'Longitude', 'LON', 'LONGITUDE', 'lng']
    
    lat_found = any(col in df.columns for col in lat_cols)
    lon_found = any(col in df.columns for col in lon_cols)
    
    return lat_found and lon_found

def get_geo_column_names(df: pd.DataFrame) -> tuple:
    """Get the actual latitude and longitude column names"""
    lat_cols = ['latitude', 'lat', 'Latitude', 'LAT', 'LATITUDE']
    lon_cols = ['longitude', 'lon', 'Longitude', 'LON', 'LONGITUDE', 'lng']
    
    lat_col = None
    lon_col = None
    
    for col in lat_cols:
        if col in df.columns:
            lat_col = col
            break
    
    for col in lon_cols:
        if col in df.columns:
            lon_col = col
            break
    
    return lat_col, lon_col

def extract_float_id(query: str, csv_path: str = "") -> str:
    """Extract float ID from query or CSV path"""
    # Try to extract from query first
    float_pattern = r'(\d{7})'
    match = re.search(float_pattern, query)
    if match:
        return match.group(1)
    
    # Try to extract from CSV path
    if csv_path:
        match = re.search(float_pattern, csv_path)
        if match:
            return match.group(1)
    
    return "Unknown Float"

def create_drift_plot(df: pd.DataFrame, query: str = "", csv_path: str = "") -> go.Figure:
    """Create drift trajectory plot using plotly"""
    lat_col, lon_col = get_geo_column_names(df)
    
    if not lat_col or not lon_col:
        return None
    
    # Extract float ID
    float_id = extract_float_id(query, csv_path)
    
    # Prepare hover data
    hover_cols = []
    if 'Date' in df.columns:
        hover_cols.append('Date')
    elif 'date' in df.columns:
        hover_cols.append('date')
    elif 'DATE' in df.columns:
        hover_cols.append('DATE')
    
    # Create the drift trajectory plot
    fig = px.line_geo(df,
                      lat=lat_col,
                      lon=lon_col,
                      hover_name=hover_cols[0] if hover_cols else None,
                      title=f'Argo Float {float_id} Drift Trajectory',
                      markers=True)
    
    # Update the map projection
    fig.update_geos(
        projection_type="natural earth",
        showcoastlines=True,
        coastlinecolor="lightgray",
        showocean=True,
        oceancolor="lightblue"
    )
    
    # Customize the line and markers
    fig.update_traces(
        line=dict(width=3, color='red'),
        marker=dict(size=8, color='darkblue'),
        hovertemplate='<b>%{hovertext}</b><br>Lat: %{lat:.4f}<br>Lon: %{lon:.4f}<extra></extra>'
    )
    
    return fig

def create_plot(df: pd.DataFrame, plot_heading: str = "Data Visualization", unique_key: str = "", query: str = "", csv_path: str = ""):
    """Create automatic plots based on the data"""
    
    if df.empty:
        st.warning("No data to plot")
        return
    
    st.subheader(plot_heading)
    
    # Check if this is a drift query and has geo data
    is_drift = is_drift_query(query)
    has_geo = has_geo_columns(df)
    
    # Auto-detect suitable plot based on data
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category', 'datetime']).columns.tolist()
    
    # Create tabs for different plot types
    if is_drift and has_geo:
        plot_tabs = st.tabs(["🗺️ Drift Map", "📊 Auto Plot", "📈 Line Chart", "📊 Bar Chart", "🔍 Scatter Plot", "📋 Raw Data"])
        
        # Drift Map tab
        with plot_tabs[0]:
            drift_fig = create_drift_plot(df, query, csv_path)
            if drift_fig:
                st.plotly_chart(drift_fig, use_container_width=True, key=f"drift_map_{unique_key}")
                
                # Additional drift statistics
                lat_col, lon_col = get_geo_column_names(df)
                if lat_col and lon_col:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Data Points", len(df))
                    with col2:
                        lat_range = df[lat_col].max() - df[lat_col].min()
                        st.metric("Latitude Range", f"{lat_range:.4f}°")
                    with col3:
                        lon_range = df[lon_col].max() - df[lon_col].min()
                        st.metric("Longitude Range", f"{lon_range:.4f}°")
            else:
                st.error("Could not create drift plot. Missing latitude/longitude columns.")
        
        tab_offset = 1
    else:
        plot_tabs = st.tabs(["📊 Auto Plot", "📈 Line Chart", "📊 Bar Chart", "🔍 Scatter Plot", "📋 Raw Data"])
        tab_offset = 0
    
    with plot_tabs[tab_offset]:  # Auto Plot
        if len(numeric_cols) >= 2:
            fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], 
                           title=f"Scatter Plot: {numeric_cols[0]} vs {numeric_cols[1]}")
            st.plotly_chart(fig, use_container_width=True, key=f"auto_scatter_{unique_key}")
        elif len(numeric_cols) == 1 and len(categorical_cols) >= 1:
            fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0],
                        title=f"Bar Chart: {numeric_cols[0]} by {categorical_cols[0]}")
            st.plotly_chart(fig, use_container_width=True, key=f"auto_bar_{unique_key}")
        elif len(numeric_cols) >= 1:
            fig = px.line(df, y=numeric_cols[0], 
                         title=f"Line Chart: {numeric_cols[0]} over Index")
            st.plotly_chart(fig, use_container_width=True, key=f"auto_line_{unique_key}")
        else:
            st.info("Data doesn't contain suitable numeric columns for plotting.")
    
    with plot_tabs[tab_offset + 1]:  # Line Chart
        if numeric_cols:
            selected_y = st.selectbox("Select Y-axis:", numeric_cols, key=f"line_y_{unique_key}")
            x_options = ["Index"] + list(df.columns)
            selected_x = st.selectbox("Select X-axis:", x_options, key=f"line_x_{unique_key}")
            
            if selected_x == "Index":
                fig = px.line(df, y=selected_y, title=f"Line Chart: {selected_y}")
            else:
                fig = px.line(df, x=selected_x, y=selected_y, 
                             title=f"Line Chart: {selected_y} vs {selected_x}")
            st.plotly_chart(fig, use_container_width=True, key=f"custom_line_{unique_key}")
        else:
            st.warning("No numeric columns available for line chart")
    
    with plot_tabs[tab_offset + 2]:  # Bar Chart
        if numeric_cols:
            selected_y = st.selectbox("Select Y-axis:", numeric_cols, key=f"bar_y_{unique_key}")
            x_options = categorical_cols + numeric_cols
            if x_options:
                selected_x = st.selectbox("Select X-axis:", x_options, key=f"bar_x_{unique_key}")
                fig = px.bar(df, x=selected_x, y=selected_y,
                           title=f"Bar Chart: {selected_y} by {selected_x}")
                st.plotly_chart(fig, use_container_width=True, key=f"custom_bar_{unique_key}")
            else:
                st.warning("No suitable columns for bar chart")
        else:
            st.warning("No numeric columns available for bar chart")
    
    with plot_tabs[tab_offset + 3]:  # Scatter Plot
        if len(numeric_cols) >= 2:
            selected_x = st.selectbox("Select X-axis:", numeric_cols, key=f"scatter_x_{unique_key}")
            selected_y = st.selectbox("Select Y-axis:", numeric_cols, key=f"scatter_y_{unique_key}")
            
            color_options = ["None"] + categorical_cols + numeric_cols
            selected_color = st.selectbox("Color by:", color_options, key=f"scatter_color_{unique_key}")
            
            if selected_color == "None":
                fig = px.scatter(df, x=selected_x, y=selected_y,
                               title=f"Scatter Plot: {selected_x} vs {selected_y}")
            else:
                fig = px.scatter(df, x=selected_x, y=selected_y, color=selected_color,
                               title=f"Scatter Plot: {selected_x} vs {selected_y}")
            st.plotly_chart(fig, use_container_width=True, key=f"custom_scatter_{unique_key}")
        else:
            st.warning("Need at least 2 numeric columns for scatter plot")
    
    with plot_tabs[tab_offset + 4]:  # Raw Data
        st.dataframe(df, use_container_width=True)
        st.info(f"Dataset shape: {df.shape[0]} rows, {df.shape[1]} columns")

def display_table_data(response: Dict[str, Any], unique_key: str = ""):
    """Display table data with enhanced features"""
    # Ensure we have a unique key
    if not unique_key:
        unique_key = f"default_{abs(hash(str(response)))}"
    
    st.subheader("📋 Data Table")
    
    # Show summary message
    if "message" in response:
        st.info(response["message"])
    
    # Display raw data
    if "raw_data" in response and response["raw_data"]:
        df = pd.DataFrame(response["raw_data"])
        
        # Add filters in sidebar
        with st.sidebar:
            st.markdown("### 🔍 Table Filters")
            
            # Column selection
            if len(df.columns) > 1:
                selected_columns = st.multiselect(
                    "Select columns to display:",
                    options=list(df.columns),
                    default=list(df.columns)[:5] if len(df.columns) > 5 else list(df.columns),
                    key=f"multiselect_cols_{unique_key}"
                )
                if selected_columns:
                    df = df[selected_columns]
            
            # Row limit
            max_rows = st.slider(
                "Max rows to display:", 
                5, 100, 20,
                key=f"slider_rows_{unique_key}"
            )
        
        # Display data
        st.dataframe(df.head(max_rows), use_container_width=True)
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name="query_results.csv",
            mime="text/csv",
            key=f"download_btn_{unique_key}"
        )
        
        # Basic statistics for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            with st.expander("📊 Data Statistics"):
                st.dataframe(df[numeric_cols].describe())

def display_theory_response(response: Dict[str, Any]):
    """Display theory/text response"""
    # Handle different response formats
    message = ""
    
    if "message" in response:
        message = response["message"]
    elif "text" in response:
        message = response["text"]
    elif isinstance(response, str):
        message = response
    else:
        message = "No response message available"
    
    st.markdown(message)

def display_plot_response(response: Dict[str, Any], unique_key: str, query: str = ""):
    """Display plot response"""
    if "message" in response:
        st.info(response["message"])
    
    if response.get("csv_url"):
        df = load_csv_from_url(response["csv_url"])
        if df is not None:
            create_plot(df, "Data Visualization", unique_key, query, response.get("csv_url", ""))

def initialize_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "Theory"

def main():
    st.set_page_config(
        page_title="Float Chat - Ocean Data Assistant",
        page_icon="🌊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Custom CSS
    st.markdown("""
    <style>
        .main-header {
            text-align: center;
            color: #1e3a8a;
            margin-bottom: 2rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 20px;
            background-color: #f0f2f6;
            border-radius: 4px 4px 0 0;
        }
        .stTabs [aria-selected="true"] {
            background-color: #1f77b4 !important;
            color: white !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.title("🌊 Float Chat")
        st.markdown("---")
        
        # Language selection
        language = st.selectbox(
            "🌐 Language:",
            ["english", "spanish", "french", "german"],
            index=0
        )
        
        st.markdown("---")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 🤖 About Float Chat")
        st.markdown("""
        **Theory Tab**: Get detailed explanations and insights about oceanographic data.
        
        **Table Tab**: Retrieve structured data in tabular format with filtering options.
        
        **Plot Tab**: Generate interactive visualizations and charts from your queries. For drift queries, an interactive map will be automatically generated.
        """)
        
        # Connection status
        try:
            response = requests.get(f"{API_BASE_URL}/", timeout=5)
            if response.status_code == 200:
                st.success("✅ Connected to backend")
            else:
                st.error("❌ Backend connection issue")
        except:
            st.error("❌ Backend unavailable")
    
    # Main header
    st.markdown('<h1 class="main-header">🌊 Float Chat - Ocean Data Assistant</h1>', unsafe_allow_html=True)
    
    # Tab selection
    tab_options = ["Theory", "Table", "Plot"]
    selected_tab = st.selectbox(
        "Select query type:",
        tab_options,
        index=tab_options.index(st.session_state.current_tab)
    )
    st.session_state.current_tab = selected_tab
    
    # Tab descriptions
    tab_descriptions = {
        "Theory": "💭 Get comprehensive explanations and insights about oceanographic concepts",
        "Table": "📋 Retrieve and analyze structured data in tabular format",
        "Plot": "📊 Generate interactive visualizations and charts from data (includes drift maps for trajectory queries)"
    }
    
    st.info(tab_descriptions[selected_tab])
    
    # Display chat history
    chat_container = st.container()
    
    with chat_container:
        for idx, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.markdown(f"**[{message.get('tab', 'Theory')}]** {message['content']}")
                else:
                    # Display based on response type
                    response = message.get("data", {})
                    unique_key = f"msg_{idx}_{abs(hash(str(response)))}"  # FIXED: Added hash for uniqueness
                    
                    if response.get("type") == "table":
                        display_table_data(response, unique_key)  # FIXED: Now passing unique_key
                    elif response.get("type") == "plot":
                        display_plot_response(response, unique_key, message.get("query", ""))
                    else:
                        display_theory_response(response)
    
    # Chat input
    if prompt := st.chat_input(f"Ask me anything about ocean data... ({selected_tab.lower()} mode)"):
        # Add user message to chat history
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt,
            "tab": selected_tab,
            "query": prompt  # Store query for drift detection
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(f"**[{selected_tab}]** {prompt}")
        
        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Processing your query..."):
                try:
                    # Call backend API
                    response = call_backend_api(prompt, selected_tab.lower(), language)
                    
                    if "error" in response:
                        st.error(response["error"])
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": response["error"]
                        })
                    else:
                        # Handle different response types
                        unique_key = f"new_{len(st.session_state.messages)}_{abs(hash(str(response)))}"  # FIXED: Added hash for uniqueness
                        
                        if response.get("type") == "table":
                            display_table_data(response, unique_key)  # FIXED: Now passing unique_key
                        elif response.get("type") == "plot":
                            display_plot_response(response, unique_key, prompt)
                        else:
                            display_theory_response(response)
                        
                        # Add assistant message to chat history
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "data": response,
                            "query": prompt  # Store query for later use
                        })
                    
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": error_msg
                    })

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>Float Chat • Powered by Streamlit & FastAPI</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
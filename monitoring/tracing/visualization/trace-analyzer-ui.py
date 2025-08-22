"""
Interactive Trace Analysis UI
Provides web-based interface for analyzing distributed traces and service dependencies.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

try:
    import networkx as nx
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    import streamlit as st
    from plotly.subplots import make_subplots

    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    st = None
    pd = None

import os
# Import our service dependency mapper
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis.service_dependency_mapper import (ServiceDependencyMapper,
                                                TraceSpan)


class TraceAnalyzerUI:
    """Interactive UI for trace analysis and visualization."""

    def __init__(self):
        self.dependency_mapper = ServiceDependencyMapper()
        self.traces_loaded = False

        if not VISUALIZATION_AVAILABLE:
            raise ImportError(
                "Visualization dependencies not available. Install streamlit, plotly, and pandas."
            )

    def run(self):
        """Run the Streamlit UI application."""
        st.set_page_config(
            page_title="Universal Platform - Trace Analysis",
            page_icon="🔍",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        st.title("🔍 Distributed Trace Analysis")
        st.markdown(
            "Analyze service dependencies, performance bottlenecks, and trace patterns"
        )

        # Sidebar for data loading and filtering
        self._render_sidebar()

        # Main content area
        if self.traces_loaded:
            self._render_main_content()
        else:
            self._render_welcome_screen()

    def _render_sidebar(self):
        """Render the sidebar with data loading and filtering options."""
        st.sidebar.header("Data Source")

        # Data loading options
        data_source = st.sidebar.selectbox(
            "Select Data Source",
            [
                "Upload JSON File",
                "Connect to Jaeger",
                "Connect to GCP Trace",
                "Sample Data",
            ],
        )

        if data_source == "Upload JSON File":
            uploaded_file = st.sidebar.file_uploader(
                "Upload trace data (JSON)",
                type=["json"],
                help="Upload a JSON file containing trace data",
            )

            if uploaded_file is not None:
                self._load_trace_data_from_file(uploaded_file)

        elif data_source == "Sample Data":
            if st.sidebar.button("Load Sample Data"):
                self._load_sample_data()

        elif data_source == "Connect to Jaeger":
            jaeger_url = st.sidebar.text_input(
                "Jaeger Query URL", "http://localhost:16686"
            )
            service_name = st.sidebar.text_input("Service Name (optional)")

            if st.sidebar.button("Connect to Jaeger"):
                self._load_trace_data_from_jaeger(jaeger_url, service_name)

        elif data_source == "Connect to GCP Trace":
            project_id = st.sidebar.text_input("GCP Project ID")

            if st.sidebar.button("Connect to GCP Trace"):
                self._load_trace_data_from_gcp(project_id)

        # Filtering options (only show if data is loaded)
        if self.traces_loaded:
            st.sidebar.header("Filters")

            # Time range filter
            time_range = st.sidebar.selectbox(
                "Time Range",
                [
                    "Last 1 hour",
                    "Last 6 hours",
                    "Last 24 hours",
                    "Last 7 days",
                    "Custom",
                ],
            )

            if time_range == "Custom":
                start_time = st.sidebar.datetime_input("Start Time")
                end_time = st.sidebar.datetime_input("End Time")

            # Service filter
            services = list(self.dependency_mapper.services.keys())
            selected_services = st.sidebar.multiselect(
                "Services", services, default=services
            )

            # Error filter
            show_errors_only = st.sidebar.checkbox("Show errors only")

            # Latency threshold
            min_latency = st.sidebar.slider(
                "Minimum Latency (ms)",
                0,
                10000,
                0,
                help="Only show traces with latency above this threshold",
            )

    def _render_welcome_screen(self):
        """Render the welcome screen when no data is loaded."""
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown(
                """
            ## Welcome to Trace Analysis
            
            Get started by loading trace data from one of these sources:
            
            ### 📁 Upload JSON File
            Upload a JSON file containing trace data in Jaeger or OpenTelemetry format.
            
            ### 🔗 Connect to Jaeger
            Connect directly to a Jaeger instance to analyze real-time traces.
            
            ### ☁️ Connect to GCP Trace
            Connect to Google Cloud Trace to analyze traces from your GCP services.
            
            ### 🎯 Sample Data
            Load sample trace data to explore the features and capabilities.
            
            ---
            
            ### Features Available:
            - 🕸️ **Service Dependency Graph** - Visualize service relationships
            - 📊 **Performance Analysis** - Identify bottlenecks and latency issues  
            - 🔍 **Error Analysis** - Track error patterns across services
            - 📈 **Metrics Dashboard** - Key performance indicators
            - 🎯 **Blast Radius Analysis** - Understand failure impact
            """
            )

    def _render_main_content(self):
        """Render the main content area with analysis tabs."""
        # Create tabs for different views
        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "📊 Dashboard",
                "🕸️ Service Graph",
                "🔍 Trace Search",
                "📈 Performance Analysis",
                "⚠️ Issues & Bottlenecks",
            ]
        )

        with tab1:
            self._render_dashboard_tab()

        with tab2:
            self._render_service_graph_tab()

        with tab3:
            self._render_trace_search_tab()

        with tab4:
            self._render_performance_tab()

        with tab5:
            self._render_issues_tab()

    def _render_dashboard_tab(self):
        """Render the main dashboard with key metrics."""
        st.header("System Overview")

        # Get topology data
        topology = self.dependency_mapper.get_service_mesh_topology()
        metrics = topology["metrics"]

        # Key metrics row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Total Services",
                value=metrics["total_services"],
                help="Number of unique services detected",
            )

        with col2:
            st.metric(
                label="Total Requests",
                value=f"{metrics['total_calls']:,}",
                help="Total number of requests across all services",
            )

        with col3:
            error_rate = (
                (metrics["total_errors"] / metrics["total_calls"]) * 100
                if metrics["total_calls"] > 0
                else 0
            )
            st.metric(
                label="Error Rate",
                value=f"{error_rate:.2f}%",
                delta=f"{metrics['total_errors']} errors",
                delta_color="inverse",
            )

        with col4:
            st.metric(
                label="Service Connections",
                value=metrics["total_connections"],
                help="Number of service-to-service connections",
            )

        # Service performance overview
        st.subheader("Service Performance Overview")

        # Prepare data for service performance table
        service_data = []
        for service_info in topology["services"]:
            service_data.append(
                {
                    "Service": service_info["name"],
                    "Environment": service_info["environment"],
                    "Requests": f"{service_info['call_count']:,}",
                    "Error Rate": f"{service_info['error_rate']:.1f}%",
                    "Avg Latency": f"{service_info['avg_latency_ms']:.1f}ms",
                    "Dependencies": service_info["dependency_count"],
                    "Dependents": service_info["dependent_count"],
                }
            )

        df_services = pd.DataFrame(service_data)
        st.dataframe(df_services, use_container_width=True)

        # Service call volume chart
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Request Volume by Service")
            service_calls = [(s["name"], s["call_count"]) for s in topology["services"]]
            service_calls.sort(key=lambda x: x[1], reverse=True)

            fig = px.bar(
                x=[s[1] for s in service_calls[:10]],
                y=[s[0] for s in service_calls[:10]],
                orientation="h",
                title="Top 10 Services by Request Volume",
            )
            fig.update_layout(xaxis_title="Requests", yaxis_title="Service")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Error Rate by Service")
            error_data = [
                (s["name"], s["error_rate"])
                for s in topology["services"]
                if s["error_rate"] > 0
            ]
            error_data.sort(key=lambda x: x[1], reverse=True)

            if error_data:
                fig = px.bar(
                    x=[s[1] for s in error_data[:10]],
                    y=[s[0] for s in error_data[:10]],
                    orientation="h",
                    title="Services with Highest Error Rates",
                    color=[s[1] for s in error_data[:10]],
                    color_continuous_scale="Reds",
                )
                fig.update_layout(xaxis_title="Error Rate (%)", yaxis_title="Service")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No errors detected in the current dataset")

    def _render_service_graph_tab(self):
        """Render the service dependency graph."""
        st.header("Service Dependency Graph")

        # Get topology data
        topology = self.dependency_mapper.get_service_mesh_topology()

        # Create networkx graph for layout
        G = nx.DiGraph()

        # Add nodes
        for service in topology["services"]:
            G.add_node(
                service["name"],
                call_count=service["call_count"],
                error_rate=service["error_rate"],
                avg_latency=service["avg_latency_ms"],
            )

        # Add edges
        for connection in topology["connections"]:
            G.add_edge(
                connection["from"],
                connection["to"],
                call_count=connection["call_count"],
                success_rate=connection["success_rate"],
            )

        # Calculate layout
        try:
            pos = nx.spring_layout(G, k=3, iterations=50)
        except:
            pos = nx.random_layout(G)

        # Create plotly graph
        edge_x = []
        edge_y = []
        edge_info = []

        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

            edge_data = G.edges[edge]
            edge_info.append(
                f"{edge[0]} → {edge[1]}<br>"
                f"Calls: {edge_data.get('call_count', 0):,}<br>"
                f"Success Rate: {edge_data.get('success_rate', 100):.1f}%"
            )

        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            line=dict(width=2, color="#888"),
            hoverinfo="none",
            mode="lines",
        )

        # Create node trace
        node_x = []
        node_y = []
        node_text = []
        node_color = []
        node_size = []

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            node_data = G.nodes[node]
            node_text.append(
                f"{node}<br>"
                f"Requests: {node_data.get('call_count', 0):,}<br>"
                f"Error Rate: {node_data.get('error_rate', 0):.1f}%<br>"
                f"Avg Latency: {node_data.get('avg_latency', 0):.1f}ms"
            )

            # Color by error rate
            error_rate = node_data.get("error_rate", 0)
            if error_rate > 5:
                node_color.append("red")
            elif error_rate > 1:
                node_color.append("orange")
            else:
                node_color.append("lightgreen")

            # Size by call count
            call_count = node_data.get("call_count", 1)
            node_size.append(min(max(call_count / 100, 10), 50))

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            hoverinfo="text",
            text=[node for node in G.nodes()],
            textposition="middle center",
            hovertext=node_text,
            marker=dict(
                size=node_size, color=node_color, line=dict(width=2, color="black")
            ),
        )

        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title="Service Dependency Graph",
                titlefont_size=16,
                showlegend=False,
                hovermode="closest",
                margin=dict(b=20, l=5, r=5, t=40),
                annotations=[
                    dict(
                        text="Node size = request volume, Color = error rate",
                        showarrow=False,
                        xref="paper",
                        yref="paper",
                        x=0.005,
                        y=-0.002,
                        xanchor="left",
                        yanchor="bottom",
                        font=dict(size=12),
                    )
                ],
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                height=600,
            ),
        )

        st.plotly_chart(fig, use_container_width=True)

        # Service details
        st.subheader("Service Connection Details")
        connection_data = []
        for conn in topology["connections"]:
            connection_data.append(
                {
                    "From": conn["from"],
                    "To": conn["to"],
                    "Requests": f"{conn['call_count']:,}",
                    "Success Rate": f"{conn['success_rate']:.1f}%",
                    "Avg Latency": f"{conn['avg_latency_ms']:.1f}ms",
                    "P95 Latency": f"{conn['p95_latency_ms']:.1f}ms",
                }
            )

        df_connections = pd.DataFrame(connection_data)
        st.dataframe(df_connections, use_container_width=True)

    def _render_trace_search_tab(self):
        """Render the trace search and details view."""
        st.header("Trace Search & Analysis")

        # Search filters
        col1, col2, col3 = st.columns(3)

        with col1:
            search_service = st.selectbox(
                "Filter by Service",
                ["All"] + list(self.dependency_mapper.services.keys()),
            )

        with col2:
            min_duration = st.number_input(
                "Min Duration (ms)", min_value=0, value=0, step=100
            )

        with col3:
            status_filter = st.selectbox("Status Filter", ["All", "Success", "Error"])

        # Display traces (simplified for demo)
        st.subheader("Recent Traces")

        # Create sample trace data for display
        traces_data = []
        for i, trace in enumerate(
            self.dependency_mapper.traces[:20]
        ):  # Show first 20 traces
            if not trace:
                continue

            root_span = min(trace, key=lambda s: s.start_time)
            total_duration = (
                max(s.start_time + timedelta(milliseconds=s.duration_ms) for s in trace)
                - root_span.start_time
            )

            error_count = sum(1 for s in trace if s.status == "ERROR")
            service_count = len(set(s.service_name for s in trace))

            traces_data.append(
                {
                    "Trace ID": root_span.trace_id[:16] + "...",
                    "Root Service": root_span.service_name,
                    "Operation": root_span.operation_name,
                    "Duration": f"{total_duration.total_seconds() * 1000:.1f}ms",
                    "Spans": len(trace),
                    "Services": service_count,
                    "Errors": error_count,
                    "Start Time": root_span.start_time.strftime("%H:%M:%S"),
                }
            )

        if traces_data:
            df_traces = pd.DataFrame(traces_data)

            # Add clickable trace selection
            event = st.dataframe(
                df_traces,
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
            )

            # Show detailed trace view if a trace is selected
            if hasattr(event, "selection") and event.selection["rows"]:
                selected_row = event.selection["rows"][0]
                st.subheader(f"Trace Details: {traces_data[selected_row]['Trace ID']}")

                # Show trace timeline (simplified)
                selected_trace = self.dependency_mapper.traces[selected_row]
                self._render_trace_timeline(selected_trace)
        else:
            st.info("No traces available for display")

    def _render_trace_timeline(self, trace_spans: List[TraceSpan]):
        """Render a timeline view of a specific trace."""
        if not trace_spans:
            return

        # Sort spans by start time
        sorted_spans = sorted(trace_spans, key=lambda s: s.start_time)
        trace_start = sorted_spans[0].start_time

        # Prepare data for Gantt chart
        gantt_data = []
        for span in sorted_spans:
            start_ms = (span.start_time - trace_start).total_seconds() * 1000
            end_ms = start_ms + span.duration_ms

            gantt_data.append(
                dict(
                    Task=f"{span.service_name}: {span.operation_name[:30]}",
                    Start=start_ms,
                    Finish=end_ms,
                    Service=span.service_name,
                    Duration=span.duration_ms,
                    Status=span.status,
                )
            )

        df_gantt = pd.DataFrame(gantt_data)

        # Create Gantt chart
        fig = px.timeline(
            df_gantt,
            x_start="Start",
            x_end="Finish",
            y="Task",
            color="Service",
            title="Trace Timeline",
            hover_data=["Duration", "Status"],
        )

        fig.update_layout(
            height=max(400, len(gantt_data) * 25),
            xaxis_title="Time (ms from trace start)",
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_performance_tab(self):
        """Render performance analysis charts and metrics."""
        st.header("Performance Analysis")

        # Get topology for performance data
        topology = self.dependency_mapper.get_service_mesh_topology()

        # Latency distribution
        st.subheader("Service Latency Distribution")

        latency_data = []
        for service in topology["services"]:
            if service["avg_latency_ms"] > 0:
                latency_data.append(
                    {
                        "Service": service["name"],
                        "Avg Latency": service["avg_latency_ms"],
                        "Call Count": service["call_count"],
                    }
                )

        if latency_data:
            df_latency = pd.DataFrame(latency_data)

            fig = px.scatter(
                df_latency,
                x="Call Count",
                y="Avg Latency",
                text="Service",
                title="Service Performance: Latency vs Volume",
                labels={"Avg Latency": "Average Latency (ms)"},
                hover_data=["Service"],
            )
            fig.update_traces(textposition="top center")
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

        # Performance recommendations
        st.subheader("Performance Recommendations")

        bottlenecks = self.dependency_mapper.find_bottlenecks(threshold_latency_ms=500)
        if bottlenecks:
            for bottleneck in bottlenecks[:5]:  # Show top 5
                if bottleneck["type"] == "high_latency":
                    st.warning(
                        f"🐌 **High Latency**: Service `{bottleneck['service']}` "
                        f"has average latency of {bottleneck['avg_latency_ms']:.1f}ms "
                        f"across {bottleneck['call_count']:,} requests."
                    )
                elif bottleneck["type"] == "high_error_rate":
                    st.error(
                        f"⚠️ **High Error Rate**: Service `{bottleneck['service']}` "
                        f"has {bottleneck['error_rate']:.1f}% error rate "
                        f"({bottleneck['error_count']} errors out of {bottleneck['call_count']} requests)."
                    )
                elif bottleneck["type"] == "high_dependency":
                    st.info(
                        f"🔗 **High Dependency**: Service `{bottleneck['service']}` "
                        f"is depended upon by {bottleneck['dependent_count']} other services. "
                        f"Consider load balancing or caching."
                    )
        else:
            st.success("✅ No significant performance bottlenecks detected!")

    def _render_issues_tab(self):
        """Render issues and bottleneck analysis."""
        st.header("Issues & Bottlenecks Analysis")

        # Find various types of issues
        bottlenecks = self.dependency_mapper.find_bottlenecks()
        circular_deps = self.dependency_mapper.detect_circular_dependencies()

        # Bottlenecks section
        st.subheader("🚨 Performance Bottlenecks")
        if bottlenecks:
            for i, bottleneck in enumerate(bottlenecks):
                with st.expander(
                    f"{bottleneck['type'].replace('_', ' ').title()}: {bottleneck['service']}"
                ):
                    if bottleneck["type"] == "high_latency":
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                "Average Latency",
                                f"{bottleneck['avg_latency_ms']:.1f}ms",
                            )
                        with col2:
                            st.metric("Request Count", f"{bottleneck['call_count']:,}")

                        st.markdown(
                            f"**Impact Score**: {bottleneck.get('impact_score', 0):,.0f}"
                        )

                    elif bottleneck["type"] == "high_error_rate":
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Error Rate", f"{bottleneck['error_rate']:.1f}%")
                        with col2:
                            st.metric("Error Count", f"{bottleneck['error_count']:,}")
                        with col3:
                            st.metric("Total Requests", f"{bottleneck['call_count']:,}")

                    elif bottleneck["type"] == "high_dependency":
                        st.metric("Dependent Services", bottleneck["dependent_count"])
                        st.write(
                            "Dependent services:", ", ".join(bottleneck["dependents"])
                        )
        else:
            st.success("No performance bottlenecks detected!")

        # Circular dependencies
        st.subheader("🔄 Circular Dependencies")
        if circular_deps:
            st.error(f"Found {len(circular_deps)} circular dependency cycles:")
            for i, cycle in enumerate(circular_deps):
                st.write(f"**Cycle {i + 1}**: {' → '.join(cycle + [cycle[0]])}")
        else:
            st.success("No circular dependencies found!")

        # Blast radius analysis
        st.subheader("💥 Blast Radius Analysis")

        services = list(self.dependency_mapper.services.keys())
        if services:
            selected_service = st.selectbox(
                "Analyze blast radius for service:", services
            )

            if st.button("Analyze Impact"):
                blast_radius = self.dependency_mapper.analyze_blast_radius(
                    selected_service
                )

                if blast_radius:
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric(
                            "Affected Services", blast_radius["affected_service_count"]
                        )

                    with col2:
                        st.metric(
                            "Total Calls Affected",
                            f"{blast_radius['total_calls_affected']:,}",
                        )

                    with col3:
                        st.metric(
                            "Blast Radius Score",
                            f"{blast_radius['blast_radius_score']:,}",
                        )

                    if blast_radius["affected_services"]:
                        st.write("**Affected Services:**")
                        st.write(", ".join(blast_radius["affected_services"]))

                    if blast_radius["critical_services_affected"]:
                        st.write("**Critical Services at Risk:**")
                        for critical in blast_radius["critical_services_affected"]:
                            st.write(
                                f"- {critical['service']} ({critical['dependent_count']} dependencies)"
                            )

    def _load_trace_data_from_file(self, uploaded_file):
        """Load trace data from uploaded JSON file."""
        try:
            trace_data = json.load(uploaded_file)
            self._process_trace_data(trace_data)
            st.sidebar.success("✅ Trace data loaded successfully!")
            self.traces_loaded = True
        except Exception as e:
            st.sidebar.error(f"Error loading file: {str(e)}")

    def _load_sample_data(self):
        """Load sample trace data for demonstration."""
        # Generate sample trace data
        import random
        from datetime import timedelta

        services = [
            "web-frontend",
            "api-gateway",
            "user-service",
            "order-service",
            "payment-service",
            "inventory-service",
            "notification-service",
        ]

        for i in range(50):  # Generate 50 sample traces
            trace_id = f"trace-{i:04d}"
            base_time = datetime.now() - timedelta(hours=random.randint(1, 24))

            spans = []

            # Create a realistic trace with multiple services
            root_span = TraceSpan(
                span_id=f"span-{i:04d}-0",
                trace_id=trace_id,
                parent_span_id="",
                service_name="web-frontend",
                operation_name="GET /orders",
                start_time=base_time,
                duration_ms=random.uniform(100, 2000),
                status="OK" if random.random() > 0.05 else "ERROR",
            )
            spans.append(root_span)

            # Add dependent service calls
            current_time = base_time + timedelta(milliseconds=10)
            parent_span_id = root_span.span_id

            for j, service in enumerate(services[1:4]):  # Add 3 more services
                span = TraceSpan(
                    span_id=f"span-{i:04d}-{j + 1}",
                    trace_id=trace_id,
                    parent_span_id=parent_span_id,
                    service_name=service,
                    operation_name="process_request",
                    start_time=current_time,
                    duration_ms=random.uniform(50, 500),
                    status="OK" if random.random() > 0.02 else "ERROR",
                )
                spans.append(span)
                current_time += timedelta(milliseconds=random.uniform(10, 100))
                parent_span_id = span.span_id

            self.dependency_mapper.add_trace(spans)

        st.sidebar.success("✅ Sample data loaded successfully!")
        self.traces_loaded = True

    def _load_trace_data_from_jaeger(self, jaeger_url: str, service_name: str = None):
        """Load trace data from Jaeger (placeholder implementation)."""
        # This would implement actual Jaeger API calls
        st.sidebar.info("Jaeger integration not implemented in this demo")

    def _load_trace_data_from_gcp(self, project_id: str):
        """Load trace data from GCP Trace (placeholder implementation)."""
        # This would implement actual GCP Trace API calls
        st.sidebar.info("GCP Trace integration not implemented in this demo")

    def _process_trace_data(self, trace_data: Dict[str, Any]):
        """Process trace data and add to dependency mapper."""
        # This would process actual trace data format
        # For now, just handle the sample data format
        pass


def main():
    """Main function to run the Streamlit app."""
    if not VISUALIZATION_AVAILABLE:
        print("Visualization dependencies not available.")
        print("Install with: pip install streamlit plotly pandas networkx")
        return

    app = TraceAnalyzerUI()
    app.run()


if __name__ == "__main__":
    main()

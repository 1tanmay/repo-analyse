import streamlit as st
from github import Github, GithubException
import re

# Set page configuration
st.set_page_config(
    page_title="Github Repo Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main { padding: 2rem; }
    .stTextInput { margin-bottom: 1rem; }
    .metrics { 
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1.5rem 0;
    }
    .metric-box {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1f77b4;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #6c757d;
    }
    </style>
""", unsafe_allow_html=True)

def get_repo_info(repo_url, token=None):
    """Extract owner and repo name from GitHub URL"""
    pattern = r'github\.com/([^/]+)/([^/]+)/?$'
    match = re.search(pattern, repo_url)
    if not match:
        return None, None
    return match.group(1), match.group(2)

def main():
    st.title("GitHub Repository Analyzer")
    
    # Sidebar for GitHub token input
    with st.sidebar:
        st.header("GitHub Authentication")
        github_token = st.text_input(
            "GitHub Personal Access Token (optional)",
            type="password",
            help="Create a token at https://github.com/settings/tokens (no permissions needed for public repos)"
        )
        st.markdown("---")
        st.markdown("### How to use")
        st.markdown("1. Enter a GitHub repository URL")
        st.markdown("2. Optionally add a GitHub token for private repos or higher rate limits")
        st.markdown("3. Click 'Analyze Repository'")
    
    # Main content
    st.header("Repository Analysis")
    repo_url = st.text_input(
        "Enter GitHub Repository URL:",
        placeholder="https://github.com/username/repository"
    )
    
    if st.button("Analyze Repository") and repo_url:
        with st.spinner("Fetching repository data..."):
            try:
                # Initialize GitHub client
                g = Github(github_token) if github_token else Github()
                
                # Get owner and repo name
                owner, repo_name = get_repo_info(repo_url)
                if not owner or not repo_name:
                    st.error("Invalid GitHub repository URL. Please enter a valid URL.")
                    return
                
                # Get repository
                repo = g.get_repo(f"{owner}/{repo_name}")
                
                # Display repository information
                st.markdown(f"## {repo.full_name}")
                
                if repo.description:
                    st.markdown(f"**Description:** {repo.description}")
                
                # Repository metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("⭐ Stars", f"{repo.stargazers_count:,}")
                with col2:
                    st.metric("🍴 Forks", f"{repo.forks_count:,}")
                with col3:
                    st.metric("👀 Watchers", f"{repo.watchers_count:,}")
                with col4:
                    st.metric("📝 Open Issues", f"{repo.open_issues_count:,}")
                
                # Additional repository information
                with st.expander("📊 More Repository Details"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("### Repository Info")
                        st.markdown(f"**Language:** {repo.language or 'Not specified'}")
                        st.markdown(f"**License:** {repo.license.spdx_id if repo.license else 'None'}")
                        st.markdown(f"**Size:** {repo.size / 1024:.1f} MB")
                        st.markdown(f"**Default Branch:** `{repo.default_branch}`")
                    
                    with col2:
                        st.markdown("### Activity")
                        st.markdown(f"**Created:** {repo.created_at.strftime('%Y-%m-%d')}")
                        st.markdown(f"**Last Updated:** {repo.updated_at.strftime('%Y-%m-%d')}")
                        st.markdown(f"**Pushed At:** {repo.pushed_at.strftime('%Y-%m-%d %H:%M')}")
                
                # Show clone URL
                with st.expander("🔗 Clone Repository"):
                    st.code(f"git clone {repo.clone_url}", language="bash")
                
            except GithubException as e:
                if e.status == 404:
                    st.error("Repository not found. Please check the URL and try again.")
                elif e.status == 401:
                    st.error("Authentication failed. Please check your GitHub token.")
                elif e.status == 403:
                    if github_token:
                        st.error("Rate limit exceeded. Please wait before making more requests.")
                    else:
                        st.error("Rate limit exceeded. Consider adding a GitHub token for higher limits.")
                else:
                    st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()

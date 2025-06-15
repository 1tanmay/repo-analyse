import streamlit as st
from github import Github, GithubException
import re
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from collections import defaultdict

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

def get_commit_activity(repo, days=30):
    """Get commit activity for the last N days"""
    since = datetime.now() - timedelta(days=days)
    commits = repo.get_commits(since=since)
    
    # Group commits by date
    commit_activity = defaultdict(int)
    for commit in commits:
        commit_date = commit.commit.author.date.date()
        commit_activity[commit_date] += 1
    
    # Convert to DataFrame for plotting
    df = pd.DataFrame(
        [{"date": date, "commits": count} for date, count in sorted(commit_activity.items())]
    )
    return df

def get_contributor_stats(repo):
    """Get contributor statistics"""
    contributors = repo.get_stats_contributors()
    if not contributors:
        return None, None
    
    # Get top 10 contributors by commits
    top_contributors = sorted(
        contributors, 
        key=lambda x: x.total if x.total else 0, 
        reverse=True
    )[:10]
    
    # Prepare data for bar chart
    contributor_data = [
        {
            "login": c.author.login if c.author else "Unknown",
            "commits": c.total,
            "additions": sum(week.a for week in c.weeks) if c.weeks else 0,
            "deletions": sum(week.d for week in c.weeks) if c.weeks else 0,
        }
        for c in top_contributors
    ]
    
    # Convert to DataFrame
    df = pd.DataFrame(contributor_data)
    return df, top_contributors

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
                    st.metric("👀 Watchers", f"{repo.subscribers_count:,}")
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
                
                # Contributor Statistics
                st.markdown("---")
                st.markdown("## 📊 Contributor Statistics")
                
                with st.spinner("Fetching contributor data..."):
                    try:
                        # Get contributor stats
                        contributors_df, top_contributors = get_contributor_stats(repo)
                        
                        if contributors_df is not None and not contributors_df.empty:
                            # Top Contributors Bar Chart
                            st.markdown("### Top Contributors by Commits")
                            fig_contributors = px.bar(
                                contributors_df,
                                x="login",
                                y="commits",
                                color="login",
                                labels={"login": "Contributor", "commits": "Number of Commits"},
                                height=400
                            )
                            st.plotly_chart(fig_contributors, use_container_width=True)
                            
                            # Add/Delete Stats
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("### Code Additions by Contributor")
                                fig_additions = px.bar(
                                    contributors_df,
                                    x="login",
                                    y="additions",
                                    color="login",
                                    labels={"login": "Contributor", "additions": "Lines Added"}
                                )
                                st.plotly_chart(fig_additions, use_container_width=True)
                            
                            with col2:
                                st.markdown("### Code Deletions by Contributor")
                                fig_deletions = px.bar(
                                    contributors_df,
                                    x="login",
                                    y="deletions",
                                    color="login",
                                    labels={"login": "Contributor", "deletions": "Lines Deleted"}
                                )
                                st.plotly_chart(fig_deletions, use_container_width=True)
                            
                            # Detailed Contributor Stats
                            with st.expander("👥 View Detailed Contributor Statistics"):
                                st.dataframe(
                                    contributors_df.rename(columns={
                                        "login": "Contributor",
                                        "commits": "Total Commits",
                                        "additions": "Total Additions",
                                        "deletions": "Total Deletions"
                                    }),
                                    use_container_width=True
                                )
                        
                        # Commit Activity
                        st.markdown("---")
                        st.markdown("## 📅 Recent Commit Activity (Last 30 Days)")
                        commit_df = get_commit_activity(repo)
                        
                        if not commit_df.empty:
                            # Commit Timeline
                            fig_commits = px.line(
                                commit_df,
                                x="date",
                                y="commits",
                                title="Daily Commits Over Time",
                                markers=True,
                                labels={"date": "Date", "commits": "Number of Commits"}
                            )
                            st.plotly_chart(fig_commits, use_container_width=True)
                            
                            # Commit Stats
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Commits (30d)", commit_df["commits"].sum())
                            with col2:
                                avg_commits = commit_df["commits"].mean()
                                st.metric("Avg. Commits/Day", f"{avg_commits:.1f}")
                            with col3:
                                busiest_day = commit_df.loc[commit_df["commits"].idxmax()]
                                st.metric("Busiest Day", f"{busiest_day['date']}: {busiest_day['commits']} commits")
                            
                            # Recent Commits Table
                            with st.expander("📝 View Recent Commits"):
                                recent_commits = repo.get_commits()[:10]  # Last 10 commits
                                commits_data = []
                                for commit in recent_commits:
                                    commit_info = commit.commit
                                    commits_data.append({
                                        "SHA": commit.sha[:7],
                                        "Message": commit_info.message.split('\n')[0][:50] + ('...' if len(commit_info.message) > 50 else ''),
                                        "Author": commit_info.author.name,
                                        "Date": commit_info.author.date.strftime('%Y-%m-%d %H:%M'),
                                        "URL": commit.html_url
                                    })
                                
                                if commits_data:
                                    st.dataframe(
                                        pd.DataFrame(commits_data),
                                        column_config={
                                            "SHA": st.column_config.TextColumn("Commit"),
                                            "Message": "Message",
                                            "Author": "Author",
                                            "Date": "Date",
                                            "URL": st.column_config.LinkColumn("Link")
                                        },
                                        hide_index=True,
                                        use_container_width=True
                                    )
                        
                    except Exception as e:
                        st.warning(f"Could not load all activity data: {str(e)}")
                
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

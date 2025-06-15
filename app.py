import streamlit as st
from github import Github, GithubException, RateLimitExceededException, BadCredentialsException, BadAttributeException
import re
from datetime import datetime, timedelta, timezone
import pandas as pd
import plotly.express as px
from collections import defaultdict
import time
import math

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

def get_commit_activity(repo, g, days=30):
    """Get commit activity for the last N days, handling pagination and rate limits."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    commit_activity = defaultdict(int)
    for i in range(days + 1):
        date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        commit_activity[date] = 0
    
    try:
        if not check_rate_limit(g):
            st.warning("⚠️ Rate limit is too low to fetch commit history.")
            return pd.DataFrame([{"date": date, "commits": 0} for date in sorted(commit_activity.keys())])

        commits_paginated_list = repo.get_commits(since=start_date, until=end_date)
        
        status_text = st.empty()
        status_text.text("Processing commits...")
        
        commit_limit = 5000 
        processed_commits = 0

        for commit in commits_paginated_list:
            if processed_commits >= commit_limit:
                st.warning(f"⚠️ Displaying activity for the last {commit_limit} commits only. The chart may be incomplete.")
                break
            
            try:
                if commit.commit and commit.commit.author and commit.commit.author.date:
                    commit_date = commit.commit.author.date.strftime('%Y-%m-%d')
                    if commit_date in commit_activity:
                        commit_activity[commit_date] += 1
                processed_commits += 1
                if processed_commits % 100 == 0:
                    status_text.text(f"Processed {processed_commits} commits...")

            except Exception:
                continue
        
        status_text.text(f"Processed {processed_commits} commits. Finalizing chart...")
        time.sleep(1)
        status_text.empty()

    except RateLimitExceededException:
        st.error("❌ GitHub API rate limit exceeded while fetching commits. Please try again later or add a GitHub token.")
        return pd.DataFrame([{"date": date, "commits": 0} for date in sorted(commit_activity.keys())])
    except Exception as e:
        st.warning(f"⚠️ Could not retrieve full commit history: {str(e)}")

    df = pd.DataFrame([{"date": date, "commits": count} for date, count in sorted(commit_activity.items())])
    return df

def check_rate_limit(g):
    """Check and display rate limit information"""
    try:
        rate_limit = g.get_rate_limit()
        core_limit = rate_limit.core
        reset_time = core_limit.reset
        remaining = core_limit.remaining
        
        if remaining == 0 and reset_time:
            # Make both datetimes timezone-aware for comparison
            from datetime import timezone
            now = datetime.now(timezone.utc)
            if reset_time.tzinfo is None:
                reset_time = reset_time.replace(tzinfo=timezone.utc)
                
            wait_time = (reset_time - now).total_seconds()
            if wait_time > 0:
                wait_minutes = math.ceil(wait_time / 60)
                st.warning(f"⚠️ Rate limit exceeded. Please wait {wait_minutes} minutes or add a GitHub token for higher limits.")
                return False
        return True
    except Exception as e:
        st.warning(f"⚠️ Could not check rate limit: {str(e)}")
        return True

def handle_github_request(func, *args, **kwargs):
    """Generic function to handle GitHub API requests with rate limit checking"""
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except RateLimitExceededException as e:
            if attempt == max_retries - 1:
                st.error("❌ GitHub API rate limit exceeded. Please try again later or add a GitHub token.")
                st.stop()
            reset_time = e.headers.get('x-ratelimit-reset')
            if reset_time:
                wait_time = int(reset_time) - int(time.time()) + 5  # Add 5s buffer
                if wait_time > 0:
                    time.sleep(min(wait_time, 60))  # Don't wait more than 60s at once
            time.sleep(retry_delay * (attempt + 1))
        except BadCredentialsException:
            st.error("❌ Invalid GitHub token. Please check your token or leave it empty for public repos.")
            st.stop()
        except BadAttributeException as e:
            st.error(f"❌ Error accessing repository data: {str(e)}")
            st.stop()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(retry_delay * (attempt + 1))
    return None

def get_contributor_stats(repo, g):
    """Get contributor statistics with rate limit handling"""
    try:
        if not check_rate_limit(g):
            return None, None
            
        # First try to get basic contributor info which is usually faster
        contributors = handle_github_request(list, repo.get_contributors())
        if not contributors:
            return None, None
            
        # Sort by number of contributions
        contributors_sorted = sorted(
            contributors,
            key=lambda x: x.contributions,
            reverse=True
        )[:10]  # Limit to top 10
        
        # Prepare data for display
        contributor_data = []
        for c in contributors_sorted:
            try:
                contributor_data.append({
                    "login": c.login,
                    "commits": c.contributions,
                    "profile_url": c.html_url,
                    "avatar_url": c.avatar_url
                })
            except Exception as e:
                st.warning(f"⚠️ Could not fetch data for one of the contributors: {str(e)}")
                continue
        
        if not contributor_data:
            return None, None
            
        return pd.DataFrame(contributor_data), contributors_sorted
        
    except Exception as e:
        st.warning(f"⚠️ Could not fetch contributor data: {str(e)}")
        return None, None

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
                # Initialize GitHub client with per_page=1 for initial rate limit check
                g = Github(github_token, per_page=1) if github_token else Github(per_page=1)
                
                # Check rate limit before proceeding
                if not check_rate_limit(g):
                    st.warning("⚠️ Rate limit is low. Some features may not be available.")
                
                # Get owner and repo name
                owner, repo_name = get_repo_info(repo_url)
                if not owner or not repo_name:
                    st.error("❌ Invalid GitHub repository URL. Please enter a valid URL.")
                    return
                
                # Get repository with rate limit handling
                repo = handle_github_request(g.get_repo, f"{owner}/{repo_name}")
                if not repo:
                    return
                
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
                
                # Get commit activity with rate limit handling
                st.markdown("---")
                st.markdown("## 📈 Commit Activity (Last 30 days)")
                
                with st.spinner("Fetching commit activity..."):
                    if not check_rate_limit(g):
                        st.warning("⚠️ Rate limit is too low to fetch commit history. Please try again later or add a GitHub token.")
                    else:
                        try:
                            commit_activity = get_commit_activity(repo, g)
                            if not commit_activity.empty:
                                # Commit Timeline
                                fig_commits = px.line(
                                    commit_activity,
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
                                    st.metric("Total Commits (30d)", commit_activity["commits"].sum())
                                with col2:
                                    avg_commits = commit_activity["commits"].mean()
                                    st.metric("Avg. Commits/Day", f"{avg_commits:.1f}")
                                with col3:
                                    busiest_day = commit_activity.loc[commit_activity["commits"].idxmax()]
                                    st.metric("Busiest Day", f"{busiest_day['date']}: {busiest_day['commits']} commits")
                                
                                # Recent Commits Table
                                with st.expander("📝 View Recent Commits"):
                                    try:
                                        commits_paginated_list = repo.get_commits()
                                        recent_commits = []
                                        for i, commit in enumerate(commits_paginated_list):
                                            if i >= 10:
                                                break
                                            recent_commits.append(commit)

                                        if recent_commits:
                                            commits_data = []
                                            for commit in recent_commits:
                                                try:
                                                    commit_info = commit.commit
                                                    author_name = commit_info.author.name if commit_info.author else "N/A"
                                                    author_date = commit_info.author.date.strftime('%Y-%m-%d %H:%M') if commit_info.author and commit_info.author.date else "N/A"
                                                    
                                                    commits_data.append({
                                                        "SHA": commit.sha[:7],
                                                        "Message": (commit_info.message.split('\n')[0][:50] + '...' if len(commit_info.message) > 50 else commit_info.message.split('\n')[0]) if commit_info.message else "No commit message",
                                                        "Author": author_name,
                                                        "Date": author_date,
                                                        "URL": commit.html_url
                                                    })
                                                except Exception:
                                                    continue # Skip malformed commits
                                            
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
                                        else:
                                            st.write("No recent commits found.")
                                    except RateLimitExceededException:
                                        st.warning("⚠️ Rate limit exceeded. Could not fetch recent commits.")
                                    except Exception as e:
                                        st.warning(f"⚠️ Could not fetch recent commits: {str(e)}")
                        except Exception as e:
                            st.warning(f"Could not load all activity data: {str(e)}")
                
                # Contributor Statistics
                st.markdown("---")
                st.markdown("## 📊 Contributor Statistics")
                
                with st.spinner("Fetching contributor data..."):
                    try:
                        # Get contributor stats with rate limit handling
                        contributors_df, top_contributors = get_contributor_stats(repo, g)
                        
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
                            
                            # Display contributor avatars and stats
                            st.markdown("### Top Contributors")
                            
                            # Create a grid of contributor cards
                            cols = st.columns(5)  # 5 columns for the grid
                            
                            for idx, (_, row) in enumerate(contributors_df.iterrows()):
                                with cols[idx % 5]:
                                    st.markdown(
                                        f"""
                                        <div style='text-align: center; margin-bottom: 1.5rem;'>
                                            <img src='{row['avatar_url']}&s=80' width='60' style='border-radius: 50%;'><br>
                                            <div style='margin-top: 0.5rem;'>
                                                <a href='{row['profile_url']}' target='_blank' style='text-decoration: none;'>
                                                    <strong>{row['login']}</strong>
                                                </a>
                                            </div>
                                            <div style='font-size: 0.9rem; color: #6c757d;'>
                                                {row['commits']:,} commits
                                            </div>
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
                            
                            # Detailed Contributor Stats
                            with st.expander("📊 View Detailed Contributor Statistics"):
                                st.dataframe(
                                    contributors_df[['login', 'commits']].rename(columns={
                                        "login": "Contributor",
                                        "commits": "Total Commits"
                                    }),
                                    use_container_width=True,
                                    column_config={
                                        "Contributor": st.column_config.TextColumn("Contributor"),
                                        "Total Commits": st.column_config.NumberColumn("Commits")
                                    },
                                    hide_index=True
                                )
                        
                    except Exception as e:
                        st.warning(f"Could not load all contributor data: {str(e)}")
                
            except GithubException as e:
                if e.status == 403 and "rate limit" in str(e).lower():
                    st.error("❌ GitHub API rate limit exceeded. Please add a GitHub token or try again later.")
                elif e.status == 404:
                    st.error("❌ Repository not found. Please check the URL and try again.")
                else:
                    st.error(f"❌ Error fetching repository data: {str(e)}")
            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
paper_browser.py
================
A Streamlit browser for the papers.jsonl archive produced by daily_papers.py.

Run:
  pip install streamlit pandas
  streamlit run paper_browser.py

If running on a remote node, forward the port from your laptop first:
  ssh -L 8501:localhost:8501 you@gpu-n34
then open http://localhost:8501 in your local browser.
"""

import os
import json
from collections import Counter

import pandas as pd
import streamlit as st

def _default_path():
    for c in [
        os.environ.get("PAPERS_JSONL"),
        "papers.jsonl",                                  # repo root (Streamlit Cloud)
        "/vast/yufeihuang/hasib_ix3/paper_archive/papers.jsonl",  # local
    ]:
        if c and os.path.exists(c):
            return c
    return "papers.jsonl"

DEFAULT_PATH = _default_path()

st.set_page_config(page_title="Paper Archive", layout="wide")


@st.cache_data
def load_papers(path):
    """Read the JSONL archive into a list of dicts (one per line)."""
    papers = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                papers.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return papers


# --------------------------------------------------------------------------- #
# Load
# --------------------------------------------------------------------------- #
st.sidebar.header("Archive")
path = st.sidebar.text_input("papers.jsonl path", DEFAULT_PATH)
if st.sidebar.button("🔄 Reload"):
    load_papers.clear()

try:
    papers = load_papers(path)
except FileNotFoundError:
    st.error(f"File not found:\n{path}")
    st.stop()

if not papers:
    st.warning("No papers in the archive yet — run daily_papers.py first.")
    st.stop()

# Filter option pools
all_topics = sorted({p.get("topic_label", "") for p in papers if p.get("topic_label")})
all_cats   = sorted({c for p in papers for c in p.get("categories", [])})

# --------------------------------------------------------------------------- #
# Filters
# --------------------------------------------------------------------------- #
st.sidebar.header("Filters")
query      = st.sidebar.text_input("Search (title / abstract / summary)")
sel_topics = st.sidebar.multiselect("Topic", all_topics)
sel_cats   = st.sidebar.multiselect("Category", all_cats)
sort_order = st.sidebar.selectbox("Sort by date", ["Newest first", "Oldest first"])


def matches(p):
    if sel_topics and p.get("topic_label") not in sel_topics:
        return False
    if sel_cats and not (set(p.get("categories", [])) & set(sel_cats)):
        return False
    if query:
        blob = f"{p.get('title','')} {p.get('abstract','')} {p.get('summary','')}".lower()
        if query.lower() not in blob:
            return False
    return True


filtered = [p for p in papers if matches(p)]
filtered.sort(key=lambda p: p.get("published", ""), reverse=(sort_order == "Newest first"))

# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #
st.title("📚 Paper Archive")
st.caption(f"Showing {len(filtered)} of {len(papers)} papers")

with st.expander("📊 Category overview", expanded=False):
    counts = Counter(c for p in filtered for c in p.get("categories", []))
    if counts:
        df = pd.DataFrame(counts.most_common(20), columns=["category", "count"]).set_index("category")
        st.bar_chart(df)
    else:
        st.write("No categories in the current selection.")

for p in filtered:
    with st.container(border=True):
        title = p.get("title", "(no title)")
        link  = p.get("link", "")
        st.markdown(f"### [{title}]({link})" if link else f"### {title}")

        meta = " · ".join(x for x in [
            p.get("published", ""),
            p.get("topic_label", ""),
            (p.get("authors", "") or "")[:120],
        ] if x)
        if meta:
            st.caption(meta)

        cats = p.get("categories", [])
        if cats:
            st.markdown(" ".join(f"`{c}`" for c in cats))

        if p.get("summary"):
            st.write(p["summary"])

        crits = p.get("critiques", [])
        if crits:
            with st.expander(f"🧐 Critiques ({len(crits)})"):
                for c in crits:
                    st.markdown(f"**{c.get('criticism','')}**")
                    if c.get("reasoning"):
                        st.write(c["reasoning"])
                    if c.get("how_to_address"):
                        st.caption("Fix: " + c["how_to_address"])
                    st.divider()

        if p.get("abstract"):
            with st.expander("📄 Abstract"):
                st.write(p["abstract"])

# Optional: download the current filtered view
st.sidebar.download_button(
    "⬇️ Download filtered (JSON)",
    data=json.dumps(filtered, ensure_ascii=False, indent=2),
    file_name="filtered_papers.json",
    mime="application/json",
)
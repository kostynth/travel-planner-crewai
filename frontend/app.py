"""Streamlit 前端入口 (占位实现)."""

import streamlit as st


def main() -> None:
    """Streamlit 应用入口."""
    st.set_page_config(
        page_title="Travel Planner CrewAI",
        page_icon="✈️",
        layout="wide",
    )
    st.title("Travel Planner CrewAI / 旅行计划师")
    st.info("占位页面: 完整界面将在后续实现.")


if __name__ == "__main__":
    main()

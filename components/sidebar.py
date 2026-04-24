def _render_agent_selector(self) -> Tuple[bool, bool]:
    """
    Render agent mode selection (Standard vs Swarm).
    
    Returns:
        Tuple of (agent_mode, swarm_mode)
    """
    st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">AGENT MODE</p>', unsafe_allow_html=True)
    
    # Get current states
    current_agent_mode = st.session_state.get("agent_mode", False)
    current_swarm_mode = st.session_state.get("swarm_mode", False)
    
    # Two-column layout for Standard/Swarm buttons
    col_a, col_b = st.columns(2)
    
    with col_a:
        if st.button(
            "🤖 Standard",
            use_container_width=True,
            type="primary" if current_agent_mode and not current_swarm_mode else "secondary",
            key="mode_standard"
        ):
            st.session_state.agent_mode = True
            st.session_state.swarm_mode = False
            st.rerun()
    
    with col_b:
        if st.button(
            "🐝 Swarm",
            use_container_width=True,
            type="primary" if current_agent_mode and current_swarm_mode else "secondary",
            key="mode_swarm"
        ):
            st.session_state.agent_mode = True
            st.session_state.swarm_mode = True
            st.rerun()
    
    # Status caption
    if current_agent_mode:
        if current_swarm_mode:
            st.caption("🐝 Swarm: Master + sub-agents (parallel execution)")
        else:
            max_steps = st.session_state.get("agent_max_steps", AppConfig.max_agent_steps)
            st.caption(f"🤖 Standard agent • {max_steps} steps max")
    else:
        st.caption("Enable agent mode for autonomous task execution")
    
    return current_agent_mode, current_swarm_mode
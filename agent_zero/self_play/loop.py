# agent_zero/self_play/loop.py
from .models import Objective, Status, Task
from .task_manager import TaskListManager
from .agent import Agent, AgentState # Import AgentState
from typing import Optional, Callable, Dict, Any

def self_play_loop(
    initial_objective_prompt: str,
    orchestrator_agent: Agent,
    task_list_manager: TaskListManager,
    max_interactions: int = 10,
    on_interaction_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    use_cloning_for_tasks: bool = True
):
    objective = Objective(description=initial_objective_prompt, initial_prompt=initial_objective_prompt)
    print(f"Starting self-play loop for objective: {objective.description[:100]}... (ID: {objective.objective_id}) by {orchestrator_agent.persona_name} ({orchestrator_agent.agent_id})")

    orchestrator_agent.current_state = AgentState.TASKED
    # print(f"{orchestrator_agent.persona_name} ({orchestrator_agent.agent_id}) state: {orchestrator_agent.current_state.value}") # Can be verbose
    orchestrator_agent.decompose_objective_into_tasks(objective, task_list_manager)

    interaction_count = 0

    while objective.status == Status.ACTIVE and interaction_count < max_interactions:
        orchestrator_agent.current_state = AgentState.TASKED
        current_loop_state_summary = { "interaction_count": interaction_count, "objective_id": objective.objective_id,"objective_description": objective.description,"objective_status": objective.status.value,"task_summary": [(t.task_id, t.description[:60], t.status.value, t.priority) for t in task_list_manager.get_all_tasks()]}
        if on_interaction_callback: on_interaction_callback(current_loop_state_summary)

        if task_list_manager.is_empty():
            if orchestrator_agent.is_objective_complete(objective, task_list_manager):
                objective.status = Status.COMPLETED
                orchestrator_agent.current_state = AgentState.IDLE
                print(f"Objective {objective.objective_id} COMPLETED. {orchestrator_agent.persona_name} state: {orchestrator_agent.current_state.value}.")
                break
            else:
                # print(f"Task list empty, objective not complete. {orchestrator_agent.persona_name} generating next steps...") # Verbose
                new_tasks = orchestrator_agent.generate_next_steps(objective, task_list_manager)
                if not new_tasks:
                    print(f"{orchestrator_agent.persona_name} could not determine next steps for objective {objective.objective_id}.")
                    # Attempt a simulated challenge if stuck
                    print(f"Transitioning {orchestrator_agent.persona_name} to attempt simulated challenge due to lack of next steps.")
                    challenge_summary = orchestrator_agent.attempt_simulated_challenge() # This method handles its own state changes internally
                    # print(f"Simulated challenge outcome for {orchestrator_agent.persona_name}: {challenge_summary if challenge_summary else 'No challenge attempted or completed.'}") # Verbose

                    objective.status = Status.REQUIRES_INTERVENTION
                    orchestrator_agent.current_state = AgentState.IDLE
                    print(f"Objective {objective.objective_id} requires intervention. {orchestrator_agent.persona_name} state: {orchestrator_agent.current_state.value}")
                    break
                task_list_manager.add_tasks(new_tasks)

        current_task = task_list_manager.get_highest_priority_task()
        if not current_task:
            # print("No pending tasks, objective not complete after attempt to generate. Loop may be stuck.") # Verbose
            if not orchestrator_agent.is_objective_complete(objective, task_list_manager):
                 objective.status = Status.REQUIRES_INTERVENTION
            else:
                 objective.status = Status.COMPLETED
            orchestrator_agent.current_state = AgentState.IDLE
            break

        # print(f"\n--- Interaction {interaction_count + 1} / {max_interactions} ---") # Verbose
        # print(f"Orchestrator {orchestrator_agent.agent_id} ({orchestrator_agent.persona_name}, State: {orchestrator_agent.current_state.value}) picked task: {current_task.description[:70]}...") # Verbose
        current_task.status = Status.IN_PROGRESS

        executor_agent = orchestrator_agent
        if use_cloning_for_tasks:
            executor_agent = orchestrator_agent.clone(agent_id_suffix=f"task_{current_task.task_id[:6]}", persona_name_override=f"Executor_{current_task.description[:10].replace(' ','_')}")
        current_task.assigned_to_agent_id = executor_agent.agent_id

        # original_executor_state = executor_agent.current_state # Not strictly needed if clone always starts IDLE
        executor_agent.current_state = AgentState.TASKED
        # print(f"Executor {executor_agent.agent_id} ({executor_agent.persona_name}, State: {executor_agent.current_state.value}) executing task.") # Verbose
        task_result, new_sub_tasks = executor_agent.execute_task(current_task, objective)
        current_task.result = task_result

        if executor_agent is not orchestrator_agent:
             executor_agent.current_state = AgentState.IDLE
        # Orchestrator remains TASKED with the main objective

        if new_sub_tasks:
            task_list_manager.add_tasks(new_sub_tasks)

        if orchestrator_agent.chroma_service:
             orchestrator_agent.reflect_and_learn_from_task(current_task)

        task_list_manager.reprioritize_tasks(objective.description)

        interaction_count += 1
        if interaction_count >= max_interactions:
            objective.status = Status.REQUIRES_INTERVENTION
            orchestrator_agent.current_state = AgentState.IDLE
            print(f"Max interactions reached. Objective requires intervention. {orchestrator_agent.persona_name} state: {orchestrator_agent.current_state.value}")
            break

    final_objective_status = objective.status.value
    if orchestrator_agent.current_state != AgentState.IDLE :
        orchestrator_agent.current_state = AgentState.IDLE
    print(f"Self-play loop finished for objective {objective.objective_id}. Final status: {final_objective_status}. Orchestrator state: {orchestrator_agent.current_state.value}")

    final_status_data = { "objective_id": objective.objective_id, "objective_description": objective.description, "final_status": final_objective_status, "total_interactions": interaction_count, "tasks": [(t.task_id, t.description, t.status.value, str(t.result)[:100]) for t in task_list_manager.get_all_tasks()]}
    if on_interaction_callback: on_interaction_callback(final_status_data)
    return objective, task_list_manager

if __name__ == '__main__':
    print("\nStarting self-play loop example from loop.py __main__...")

    from agent_zero.agent_configs import load_agent_from_config

    orchestrator_config = load_agent_from_config("DefaultOrchestrator")
    if not orchestrator_config:
        print("CRITICAL: Could not load DefaultOrchestrator config. Exiting example.")
        exit()

    # Example: Override a RAG parameter from the loaded config if needed
    # orchestrator_config['rag_results_count'] = 5

    main_orchestrator = Agent(**orchestrator_config)

    tasks_manager = TaskListManager()

    objective_prompt = "Learn about the Great Pyramid of Giza by scraping its Wikipedia page, then explain its historical significance and construction theories. Finally, reflect on the process of information gathering and explanation."

    def print_interaction_update(data: Dict[str, Any]):
        print("-" * 40)
        status = data.get('objective_status', data.get('final_status', 'Unknown'))
        interaction = data.get('interaction_count', 'N/A')
        obj_desc_short = data.get('objective_description', '')[:60]

        print(f"LOOP INTERACTION: {interaction} | OBJECTIVE: '{obj_desc_short}...' | STATUS: {status}")

        tasks = data.get("task_summary", [])
        if tasks:
            pending_tasks = [t for t in tasks if t[2] == Status.PENDING.value]
            inprogress_tasks = [t for t in tasks if t[2] == Status.IN_PROGRESS.value]
            # completed_tasks = [t for t in tasks if t[2] == Status.COMPLETED.value] # Less critical for live update

            if pending_tasks:
                print(f"  Pending ({len(pending_tasks)}):")
                for tid, desc, _, prio in sorted(pending_tasks, key=lambda x: x[3], reverse=True)[:2]:
                    print(f"    - P{prio} (ID:{tid[:4]}) {desc[:50]}...")
            if inprogress_tasks:
                print(f"  In Progress ({len(inprogress_tasks)}):")
                for tid, desc, _, prio in inprogress_tasks:
                    print(f"    - P{prio} (ID:{tid[:4]}) {desc[:50]}...")
        print("-" * 40)

    print(f"\nRunning self_play_loop for objective: '{objective_prompt}'")
    final_objective_state, resulting_tasks_manager = self_play_loop(
       initial_objective_prompt=objective_prompt,
       orchestrator_agent=main_orchestrator,
       task_list_manager=tasks_manager,
       max_interactions=15,
       on_interaction_callback=print_interaction_update,
       use_cloning_for_tasks=True
    )
    print("--- SELF-PLAY EXAMPLE FINISHED ---")

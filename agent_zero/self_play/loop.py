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
    print(f"{orchestrator_agent.persona_name} ({orchestrator_agent.agent_id}) state: {orchestrator_agent.current_state.value}")
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
                print(f"Task list empty, objective not complete. {orchestrator_agent.persona_name} generating next steps...")
                new_tasks = orchestrator_agent.generate_next_steps(objective, task_list_manager)
                if not new_tasks:
                    print(f"{orchestrator_agent.persona_name} could not determine next steps for objective {objective.objective_id}.")
                    # Attempt a simulated challenge if stuck
                    print(f"Transitioning {orchestrator_agent.persona_name} to attempt simulated challenge due to lack of next steps.")
                    challenge_summary = orchestrator_agent.attempt_simulated_challenge() # This method handles its own state changes internally
                    print(f"Simulated challenge outcome for {orchestrator_agent.persona_name}: {challenge_summary if challenge_summary else 'No challenge attempted or completed.'}")

                    objective.status = Status.REQUIRES_INTERVENTION
                    orchestrator_agent.current_state = AgentState.IDLE
                    print(f"Objective {objective.objective_id} requires intervention. {orchestrator_agent.persona_name} state: {orchestrator_agent.current_state.value}")
                    break
                task_list_manager.add_tasks(new_tasks)

        current_task = task_list_manager.get_highest_priority_task()
        if not current_task:
            print("No pending tasks, objective not complete after attempt to generate. Loop may be stuck.")
            if not orchestrator_agent.is_objective_complete(objective, task_list_manager):
                 objective.status = Status.REQUIRES_INTERVENTION
            else:
                 objective.status = Status.COMPLETED
            orchestrator_agent.current_state = AgentState.IDLE # Set idle before breaking
            break

        print(f"\n--- Interaction {interaction_count + 1} / {max_interactions} ---")
        # Orchestrator is TASKED with managing this task
        # orchestrator_agent.current_state = AgentState.TASKED # Already set at loop start
        print(f"Orchestrator {orchestrator_agent.agent_id} ({orchestrator_agent.persona_name}, State: {orchestrator_agent.current_state.value}) picked task: {current_task.description[:70]}...")
        current_task.status = Status.IN_PROGRESS

        executor_agent = orchestrator_agent
        if use_cloning_for_tasks:
            executor_agent = orchestrator_agent.clone(agent_id_suffix=f"task_{current_task.task_id[:6]}", persona_name_override=f"Executor_{current_task.description[:10].replace(' ','_')}")
        current_task.assigned_to_agent_id = executor_agent.agent_id

        original_executor_state = executor_agent.current_state # Should be IDLE if clone
        executor_agent.current_state = AgentState.TASKED
        # print(f"Executor {executor_agent.agent_id} ({executor_agent.persona_name}, State: {executor_agent.current_state.value}) executing task.") # Less verbose
        task_result, new_sub_tasks = executor_agent.execute_task(current_task, objective)
        current_task.result = task_result
        # Task status (COMPLETED/FAILED) is set by execute_task

        if executor_agent is not orchestrator_agent:
             executor_agent.current_state = AgentState.IDLE
        else: # Orchestrator executed the task itself
             orchestrator_agent.current_state = AgentState.TASKED # Still tasked with objective

        if new_sub_tasks:
            task_list_manager.add_tasks(new_sub_tasks)

        if orchestrator_agent.chroma_service:
             # print(f"Orchestrator {orchestrator_agent.agent_id} reflecting on task: {current_task.task_id[:8]}") # Less verbose
             orchestrator_agent.reflect_and_learn_from_task(current_task)

        task_list_manager.reprioritize_tasks(objective.description)

        interaction_count += 1
        if interaction_count >= max_interactions:
            objective.status = Status.REQUIRES_INTERVENTION
            orchestrator_agent.current_state = AgentState.IDLE
            print(f"Max interactions reached. Objective requires intervention. {orchestrator_agent.persona_name} state: {orchestrator_agent.current_state.value}")
            break

    # Loop finished
    final_objective_status = objective.status.value
    if orchestrator_agent.current_state != AgentState.IDLE : # Ensure it's IDLE if loop ends for other reasons than explicit completion/intervention
        orchestrator_agent.current_state = AgentState.IDLE
    print(f"Self-play loop finished for objective {objective.objective_id}. Final status: {final_objective_status}. Orchestrator state: {orchestrator_agent.current_state.value}")

    final_status_data = { "objective_id": objective.objective_id, "objective_description": objective.description, "final_status": final_objective_status, "total_interactions": interaction_count, "tasks": [(t.task_id, t.description, t.status.value, str(t.result)[:100]) for t in task_list_manager.get_all_tasks()]}
    if on_interaction_callback: on_interaction_callback(final_status_data)
        return objective, task_list_manager

if __name__ == '__main__':
    # Example Usage:
    print("Starting self-play loop example (Orchestrator Agent)...")
    # Agent is now "Orchestrator" by default if persona_name isn't specified.
    # Explicitly setting it for clarity in the example if desired, or use the default.
    main_orchestrator = Agent(persona_name="MainOrchestrator") # Example of explicit naming
    # tasks_manager = TaskListManager()
    # creative_objective = "Write a short poem about a lonely lighthouse on a distant planet, then explain the poem's themes."
    # research_objective = "Explore the concept of 'Zero-Knowledge Proofs' and explain its main applications, then outline how one might build a simple ZKP system."

    # # Example of manually pre-seeding memory for testing RAG
    # # main_orchestrator.process_and_store_text_in_memory(
    # #    text_content="LangChain is a framework for developing applications powered by language models. It has many components for building complex LLM workflows.",
    # #    source_metadata={'source_type': 'manual_knowledge', 'doc_id': 'lc_info_001'},
    # #    collection_name="my_test_collection" # Can use a specific collection
    # # )
    # # objective_prompt = "What is LangChain and what are its components?"
    # # objective_prompt = creative_objective # Default for this example run


    # def print_interaction_update(data):
    #    # (Same callback as before)
    #    loop_stage = "UPDATE" if "interaction_count" in data and data["interaction_count"] < 7 else "FINAL" # Assuming max_interactions = 7 for this example
    #    print(f"LOOP {loop_stage}: Int {data.get('interaction_count', 'N/A')}, Obj: {data.get('objective_description', '')[:40]}..., Status: {data.get('objective_status', data.get('final_status'))}")
    #    if "task_summary" in data and loop_stage == "UPDATE":
    #        print("  Tasks (Top 3 Pending/In-Progress):")
    #        pending_or_progress = [ts for ts in data["task_summary"] if ts[2] in [Status.PENDING.value, Status.IN_PROGRESS.value]]
    #        pending_or_progress.sort(key=lambda x: x[3], reverse=True)
    #        for tid, desc, status, prio in pending_or_progress[:3]:
    #            print(f"    - ID {tid[:4]} P{prio}: {desc[:50]}... ({status})")

    # final_objective_state, resulting_tasks_manager = self_play_loop(
    #    initial_objective_prompt=creative_objective,
    #    orchestrator_agent=main_orchestrator,
    #    task_list_manager=tasks_manager,
    #    max_interactions=7,
    #    on_interaction_callback=print_interaction_update,
    #    use_cloning_for_tasks=True # Test with cloning enabled
    # )
    # # ... (rest of example output)
    pass

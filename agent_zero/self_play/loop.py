# agent_zero/self_play/loop.py
from .models import Objective, Status, Task
from .task_manager import TaskListManager
from .agent import Agent
from typing import Optional, Callable, Dict, Any

def self_play_loop(
    initial_objective_prompt: str,
    orchestrator_agent: Agent,
    task_list_manager: TaskListManager,
    max_interactions: int = 10,
    on_interaction_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    use_cloning_for_tasks: bool = True # Added flag to control cloning
):
    objective = Objective(description=initial_objective_prompt, initial_prompt=initial_objective_prompt)
    print(f"Starting self-play loop for objective: {objective.description[:100]}... (ID: {objective.objective_id})")
    print(f"Cloning for tasks is {'ENABLED' if use_cloning_for_tasks else 'DISABLED'}")

    orchestrator_agent.decompose_objective_into_tasks(objective, task_list_manager)

    interaction_count = 0

    while objective.status == Status.ACTIVE and interaction_count < max_interactions:
        current_loop_state_summary = {
            "interaction_count": interaction_count,
            "objective_id": objective.objective_id,
            "objective_description": objective.description,
            "objective_status": objective.status.value,
            "task_summary": [(t.task_id, t.description[:60], t.status.value, t.priority) for t in task_list_manager.get_all_tasks()]
        }
        if on_interaction_callback:
            on_interaction_callback(current_loop_state_summary)

        if task_list_manager.is_empty():
            if orchestrator_agent.is_objective_complete(objective, task_list_manager):
                objective.status = Status.COMPLETED
                print(f"Objective {objective.objective_id} marked as COMPLETED by agent {orchestrator_agent.agent_id} ({orchestrator_agent.persona_name}).")
                break
            else:
                print(f"Task list empty, objective not judged complete. Orchestrator {orchestrator_agent.agent_id} ({orchestrator_agent.persona_name}) generating next steps...")
                new_tasks = orchestrator_agent.generate_next_steps(objective, task_list_manager)
                if not new_tasks:
                    objective.status = Status.REQUIRES_INTERVENTION
                    print(f"Orchestrator {orchestrator_agent.agent_id} ({orchestrator_agent.persona_name}) could not determine next steps for objective {objective.objective_id}. Requires intervention.")
                    break
                task_list_manager.add_tasks(new_tasks)

        current_task = task_list_manager.get_highest_priority_task()
        if not current_task:
            print("No pending tasks available after attempting to generate new ones. Objective may be stuck or complete.")
            if not orchestrator_agent.is_objective_complete(objective, task_list_manager):
                 objective.status = Status.REQUIRES_INTERVENTION
            else:
                 objective.status = Status.COMPLETED
            break

        print(f"\n--- Interaction {interaction_count + 1} / {max_interactions} ---")
        print(f"Orchestrator {orchestrator_agent.agent_id} ({orchestrator_agent.persona_name}) picked task (ID: {current_task.task_id[:8]}, Prio {current_task.priority}): {current_task.description}")
        current_task.status = Status.IN_PROGRESS

        if use_cloning_for_tasks:
            # Clone an agent for this specific task
            executor_agent = orchestrator_agent.clone(
                agent_id_suffix=f"task_{current_task.task_id[:8]}",
                persona_name_override=f"TaskExecutor_{current_task.description[:15].replace(' ','_')}"
            )
            current_task.assigned_to_agent_id = executor_agent.agent_id
        else:
            executor_agent = orchestrator_agent
            current_task.assigned_to_agent_id = orchestrator_agent.agent_id

        print(f"Executor agent {executor_agent.agent_id} ({executor_agent.persona_name}) executing task.")
        task_result, new_sub_tasks = executor_agent.execute_task(current_task, objective)
        current_task.result = task_result
        # Status (COMPLETED/FAILED) is set within execute_task by the executor

        if new_sub_tasks:
            print(f"Executor {executor_agent.agent_id} ({executor_agent.persona_name}) generated {len(new_sub_tasks)} new sub-tasks from task {current_task.task_id[:8]}.")
            task_list_manager.add_tasks(new_sub_tasks)

        task_list_manager.reprioritize_tasks(objective.description)

        interaction_count += 1
        if interaction_count >= max_interactions:
            objective.status = Status.REQUIRES_INTERVENTION
            print(f"Max interactions ({max_interactions}) reached for objective {objective.objective_id}. Requires intervention.")
            break

        final_status_data = {
            "objective_id": objective.objective_id,
            "objective_description": objective.description,
            "final_status": objective.status.value,
            "total_interactions": interaction_count,
            "tasks": [(t.task_id, t.description, t.status.value, str(t.result)[:100]) for t in task_list_manager.get_all_tasks()]
        }
        if on_interaction_callback:
             on_interaction_callback(final_status_data)

        print(f"Self-play loop finished for objective {objective.objective_id}. Final status: {objective.status.value}")
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

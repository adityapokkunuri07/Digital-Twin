from typing import List, Dict, Any, Tuple, Set

class FeasibilityValidator:
    @staticmethod
    def validate_config(workflow_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates workflow configurations for sequence safety and parameter satisfaction.
        Returns:
            Tuple[bool, List[str]]: (is_feasible, list_of_error_messages)
        """
        errors = []
        steps = workflow_config.get("steps", [])
        if not steps:
            return True, []

        # 1. Map step IDs to step definitions
        step_map = {step["id"]: step for step in steps if "id" in step}
        
        # Check for duplicate step IDs
        if len(step_map) != len(steps):
            errors.append("Validation Error: Workflow contains duplicate step IDs.")

        # 2. Cycle Detection (Topological Sort / DFS)
        visited = {} # state: 0 = unvisited, 1 = visiting, 2 = visited
        
        NODE_PHASE_ORDER = {
            "data_gathering": 1,
            "processing": 2,
            "human_intercept": 3,
            "action_dispatch": 4
        }
        
        def has_cycle(step_id: str) -> bool:
            if step_id not in visited:
                return False
            if visited[step_id] == 1:
                return True # Found cycle
            if visited[step_id] == 2:
                return False

            visited[step_id] = 1
            step = step_map.get(step_id, {})
            step_phase = NODE_PHASE_ORDER.get(step.get("node_type", "processing"), 2)
            
            for dep_id in step.get("dependencies", []):
                dep_step = step_map.get(dep_id)
                if not dep_step:
                    errors.append(f"Validation Error: Step '{step_id}' depends on non-existent step '{dep_id}'.")
                    continue
                    
                dep_phase = NODE_PHASE_ORDER.get(dep_step.get("node_type", "processing"), 2)
                if step_phase < dep_phase:
                    errors.append(f"Validation Error: Phase mismatch. Step '{step_id}' ({step.get('node_type', 'processing')}) cannot depend on step '{dep_id}' ({dep_step.get('node_type', 'processing')}) because it executes earlier in the Zero-Trust lifecycle.")
                    
                if has_cycle(dep_id):
                    return True
            
            visited[step_id] = 2
            return False

        # Initialize visit state
        for sid in step_map:
            visited[sid] = 0

        cycle_detected = False
        for sid in step_map:
            if visited[sid] == 0:
                if has_cycle(sid):
                    cycle_detected = True
                    errors.append("Validation Error: Cyclic dependency loop detected in step execution graph.")
                    break

        # If there's a cycle, we stop validation early as ordering is invalid
        if cycle_detected:
            return False, errors

        # 3. Variable Propagation & Parameter Coverage Validation
        # Run a simulated execution matching topological order to verify input variable resolution
        # Let's perform a simple topological sort to simulate step execution
        resolved_order = []
        vis_state = {sid: False for sid in step_map}

        def topo_sort(sid: str):
            if vis_state[sid]:
                return
            step = step_map[sid]
            for dep_id in step.get("dependencies", []):
                if dep_id in step_map:
                    topo_sort(dep_id)
            vis_state[sid] = True
            resolved_order.append(sid)

        for sid in step_map:
            if not vis_state[sid]:
                topo_sort(sid)

        # Track set of available variables produced during simulated execution
        available_variables: Set[str] = set()
        
        for sid in resolved_order:
            step = step_map[sid]
            inputs = step.get("inputs", [])
            outputs = step.get("outputs", [])
            
            # Check inputs satisfaction
            unsatisfied_inputs = [inp for inp in inputs if inp not in available_variables]
            if unsatisfied_inputs:
                errors.append(
                    f"Validation Error: Step '{step.get('name', sid)}' requires inputs {unsatisfied_inputs} "
                    f"which are not produced by any preceding dependent steps."
                )
            
            # Add step outputs to available scope
            for out in outputs:
                available_variables.add(out)

        is_feasible = len(errors) == 0
        return is_feasible, errors

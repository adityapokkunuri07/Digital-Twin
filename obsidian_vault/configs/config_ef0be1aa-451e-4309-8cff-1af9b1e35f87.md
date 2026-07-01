---
id: ef0be1aa-451e-4309-8cff-1af9b1e35f87
expert_id: None
version: 1.0.0
feasible: false
errors: ["Validation Error: Step 'step_1' depends on non-existent step 'step-1'."]
type: twin_config
---

# Twin Workflow Configuration: ef0be1aa-451e-4309-8cff-1af9b1e35f87

## Configuration Workflow Steps

### Step: Vitals Intake (ID: step_1)
- **Inputs**: 
- **Outputs**: temperature, chest_pain
- **Dependencies**: step-1

### Step: temperature, chest_pain (ID: step_2)
- **Inputs**: temperature
- **Outputs**: fever_severity
- **Dependencies**: step_1

### Step: Cardiac Assessment (ID: step_3)
- **Inputs**: chest_pain
- **Outputs**: cardiac_risk
- **Dependencies**: step_2

### Step: Final Triage Gate (ID: step_4)
- **Inputs**: fever_severity, cardiac_risk
- **Outputs**: final_decision
- **Dependencies**: step_2, step_3

## Associated Chain of Thought (CoT) Nodes

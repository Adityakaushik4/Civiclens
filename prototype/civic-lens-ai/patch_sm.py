import sys

with open("app/escalation/state_machine.py", "r") as f:
    content = f.read()

def inject_validation(method_name, to_status, content):
    target = f"def {method_name}(\n"
    start_idx = content.find(target)
    if start_idx == -1:
        return content
        
    old_status_line = "old_status = record.current_status\n"
    insert_idx = content.find(old_status_line, start_idx)
    if insert_idx == -1:
        return content
    insert_idx += len(old_status_line)
    
    validation_code = f"        if {to_status} not in self.VALID_TRANSITIONS.get(old_status, []):\n            raise ValueError(f\"Invalid transition from {{old_status}} to {to_status}\")\n"
    
    return content[:insert_idx] + validation_code + content[insert_idx:]

content = inject_validation("acknowledge_issue", "IssueStatus.ACKNOWLEDGED", content)
content = inject_validation("start_work", "IssueStatus.IN_PROGRESS", content)
content = inject_validation("submit_completion", "IssueStatus.AWAITING_VERIFICATION", content)

with open("app/escalation/state_machine.py", "w") as f:
    f.write(content)

print("Patched state machine transitions.")

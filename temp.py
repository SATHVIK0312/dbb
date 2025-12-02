planned_steps = 0
            for line in script_content.splitlines():
                line = line.strip()
                if not_comment = not line.startswith('#')
                if line and not_comment and any(re.search(p, line) for p in action_patterns):
                    planned_steps += 1

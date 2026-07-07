def escalate_to_human(subtask_description: str, last_result: str, reason: str) -> str:
    print("\n" + "=" * 70)
    print("HUMAN INPUT NEEDED")
    print("=" * 70)
    print(f"Subtask:           {subtask_description}")
    print(f"Escalated because: {reason}")
    print("-" * 70)
    print("Specialist's last attempt:")
    print(last_result)
    print("-" * 70)
    print("Options:")
    print("  [Enter]      Accept the last attempt as-is")
    print("  [type text]  Provide a corrected answer to use instead")
    print("=" * 70)

    human_input = input("Your response: ").strip()

    if human_input == "":
        print("[HUMAN] Accepted specialist's last attempt as-is.\n")
        return last_result

    print("[HUMAN] Provided a replacement answer.\n")
    return human_input
# Auth Token
aws sso login --profile dev

aws quicksight list-spaces \
  --aws-account-id <ACCOUNT-ID> --profile dev

aws quicksight list-space-resources \
  --aws-account-id <ACCOUNT-ID> --space-id <id> --profile dev

aws quicksight describe-space \
  --aws-account-id <ACCOUNT-ID> --space-id <id> --profile dev



aws quicksight list-agents --aws-account-id <ACCOUNT-ID> --profile dev


# Engineering Onboard Specialist
aws quicksight describe-agent --aws-account-id <ACCOUNT-ID> --agent-id 093ac4e3-0712-481e-af95-9ddc5e4fc734 --profile dev





Prompt to run audit:
```
Run the Quick chat audit (bank v1) against the Engineering Onboarding Specialist agent, per quick_chat_audits/question_bank.md. Re-auth AWS SSO if needed, take the snapshots, then open Quick in the browser pane and give me the 8 questions to ask in a fresh chat. When I say done, capture the transcript, grade it, and write the run artifacts.
```
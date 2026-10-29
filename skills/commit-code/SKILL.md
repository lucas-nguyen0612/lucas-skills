---
name: commit-code
description: Automatically generate a commit message based on staged/unstaged changes with the current branch name as prefix, then commit the code.
---

# Smart Commit Skill

This skill automates the git commit process by analyzing changed files and generating a meaningful commit message with the current branch name as a prefix.

## When to Use

Use this skill when the user asks to:
- Commit code
- Create a commit with an auto-generated message
- Use `/commit-code` or similar commit-related requests

## Steps

### Step 1: Read the current branch name

Run the following command to get the current git branch name:

```bash
git rev-parse --abbrev-ref HEAD
```

Store the branch name for use as the commit message prefix.

### Step 2: Check for staged changes

Run the following command to check if there are any staged changes:

```bash
git diff --cached --name-only
```

### Step 3: Read changed files (unstaged + staged)

If there are **no staged changes**, read ALL uncommitted changes (both staged and unstaged):

```bash
git diff --stat
git diff
```

If there **are staged changes**, only read the staged changes (these are what will be committed):

```bash
git diff --cached --stat
git diff --cached
```

This gives you the full diff of all changes that will be committed.

Also run this to check for any new untracked files:

```bash
git status --short
```

Files marked with `??` are untracked and need to be explicitly staged if they should be included.

### Step 4: Analyze and generate commit message

Based on the diff output from Step 3, analyze the changes and generate a concise, descriptive commit message.

**Commit message format:**

```
(fix|feat|enhance|refactor,...): <story/task> - <summary of changes>.

- <detail 1>
- <detail 2>
- ...
```

**Rules for the commit message:**
1. The prefix MUST be the type of change (fix, feat, enhance, or refactor,...) in parentheses, followed by a colon and space.
2. The next part MUST be the story/task identifier (from the branch name or context).
3. Followed by a hyphen and the concise summary of content changes.
4. The summary line should be under 72 characters and end with a period.
5. Use present tense (e.g., "add feature" not "added feature").
6. The body should list the key changes as bullet points.
7. Group related changes together.
8. Write the commit message in English.

**Examples:**

```
(feat): story-5-9-pcms-catalog - add product variant management.

- Add create/edit forms for product variants
- Implement variant validation logic
- Update product detail page to show variants
```

```
(fix): feature/auth - fix login redirect issue.

- Fix redirect loop after successful login
- Add proper error handling for expired tokens
```

### Step 5: Present the commit message to the user

Present the generated commit message to the user. Show:
1. The list of files that will be committed
2. The proposed commit message

Then, ask the following questions:
1. Do you want to commit to this message?
2. Do you want to add anything to the message?
3. Do you want to create a description for the PR?

### Step 6: Stage and commit

Once the user confirms:

1. If there are no staged changes, stage all changes:
```bash
git add -A
```

2. If the user only wants to commit specific files, stage only those files:
```bash
git add <file1> <file2> ...
```

3. Commit with the generated (or user-modified) message:
```bash
git commit -m "<commit_message>"
```

### Step 7: Confirm success

After the commit is successful, show the user:
- The commit hash
- The commit message
- The number of files changed

Run:
```bash
git log -1 --oneline
```

### Step 8: Generate PR Description (If requested)

If the user answered "Yes" to question 3 in Step 5 ("Do you want to create a description for the PR?"):
1. Read the `pr_description_template.md` file located in the `templates` subdirectory of this skill (`.gemini/skills/smart-commit/templates/pr_description_template.md`).
2. Generate the PR description based on the analyzed code changes and the provided template.
3. Present the generated PR description to the user.

## Notes

- **Never force push** or push to remote automatically. Only commit locally.
- If the user wants to push after committing, they should explicitly ask.
- If there are merge conflicts or other git issues, report them clearly to the user.
- If the diff is very large, summarize the key changes rather than listing every single modification.
- Always respect `.gitignore` — do not stage ignored files.

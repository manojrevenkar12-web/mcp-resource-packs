# Deployment Kit: Wingtip Logistics

Follow the steps in order. Each step says what to do, who to ask and how you know it is finished.

## Step 1. Connect the workspace

Ask the customer's Smartsheet admin to connect their workspace to the MCP server in the AI tool they use
(Claude, Copilot, ChatGPT or Gemini). Finished when the admin can ask the assistant "which projects are
listed?" and gets their project names back.

## Step 2. Confirm what the draft could not be sure about

The draft read 13 sheets and was unsure about 5 things. Ask the admin each
question below and record the answer in the review screen. Finished when every question has an answer.

1. In "Data Expansion" and sheets like it, does the column "Zustand" hold the traffic-light status (on track, at risk, off track)?
2. In "Data Expansion" and sheets like it, does the column "Erledigt %" hold how complete the task is?
3. In "Data Expansion" and sheets like it, does the column "Abgeschlossen" hold the tick box that says a task is signed off?
4. When a row's status says "On Plan", does that mean on track?
5. When a row's status says "Slipping", does that mean at risk?

## Step 3. Run the workshop

Book an hour with the people who run the projects. Ask the questions in WORKSHOP.md and record the answers.
Finished when every rule in WORKSHOP.md has an answer.

## Step 4. Check the answers against the customer's own questions

Ask the 60 questions in ACCEPTANCE.md. Finished when the lower bound is at least
85%. Now: 57 of 60 right, lower bound 86.3%.

## Step 5. Switch on the weekly status lines

Pattern: **maker checker**. Why: one agent alone was wrong on 0 of 16 pilot lines; at 95% confidence that could be 14%, above the 0% the customer accepts.

## Step 6. Hand over

Walk the customer's admin through this kit. Finished when they can say which sheets the assistant reads,
what "at risk" means for them, and who to call when an answer looks wrong.


# SYSTEM ARCHITECTURE

Outlook

↓

Workflow Engine

↓

Queue Manager

↓

queue.json

↓

Dashboard

↓

Engineer

↓

Outlook Sender

QueueManager is the Single Source of Truth.

Workflow only produces data.

Dashboard only displays data.

Business Logic belongs only inside QueueManager.
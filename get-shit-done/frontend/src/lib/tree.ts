import { Task } from "../types";

export interface TaskNode { task: Task; children: TaskNode[] }

export function buildTree(tasks: Task[]): TaskNode[] {
  const byId = new Map<number, TaskNode>();
  tasks.forEach((t) => byId.set(t.id, { task: t, children: [] }));
  const roots: TaskNode[] = [];
  for (const node of byId.values()) {
    const pid = node.task.parent_task_id;
    if (pid != null && byId.has(pid)) byId.get(pid)!.children.push(node);
    else roots.push(node);
  }
  return roots;
}
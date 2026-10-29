export interface Task {
  id: number;
  goal_id: number | null;
  parent_task_id: number | null;
  title: string;
  outcome: string;
  smallest_first_action: string;
  priority: number;
  estimated_minutes: number;
  actual_minutes: number;
  status: string;
  scheduled_start: string | null;
  scheduled_end: string | null;
  postpone_count: number;
  blocker: string;
  task_type: string;
  subtask_progress?: { done: number; total: number };   // ← add
}

export interface Goal {
  id: number;
  title: string;
  target_outcome: string;
  week_start: string;
  priority: number;
  status: string;
}

export interface Prefs {
  coaching_style: string;
  custom_instructions: string;
  hydration_goal_ml: number;
  work_hours_start: string;
  work_hours_end: string;
  motivational_prompts: boolean;
  autonomy_level: string;
  theme: string;
  accent_color: string;
  bg_image: string;
  bg_opacity: number;
}

export interface Dashboard {
  today_tasks: Task[];
  next_task: Task | null;
  completed_today: number;
  planned_today: number;
  focus_minutes_today: number;
  overdue_count: number;
  blocked_count: number;
  weekly_goal_progress: { goal_id: number; title: string; completed: number; total: number; progress_pct: number }[];
  hydration_ml_today: number;
  hydration_goal_ml: number;
  mood_energy: { logged_at: string; mood: number | null; energy: number | null }[];
  agent_summary: string;
}

export interface MoodEntry {
  id: number;
  logged_at: string;
  mood: number | null;
  energy: number | null;
  notes: string;
}

export interface FoodEntry {
  id: number;
  logged_at: string;
  meal_type: string;
  description: string;
  notes: string;
}
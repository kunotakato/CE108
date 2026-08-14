export type Role = "student" | "teacher" | "admin";

export type User = {
  id: number;
  email: string;
  role: Role;
  display_name: string;
  grade?: string | null;
  diagnostic_completed?: number;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: User;
};

export type DailyPlanItem = {
  id: number;
  plan_id: number;
  question_id: number;
  item_type: string;
  display_order: number;
  reason: string;
  question_text: string;
  question_type: QuestionType;
  importance: number;
  subject_name: string;
  topic_name: string;
  completed: number;
};

export type DailyPlan = {
  id: number;
  plan_date: string;
  mode?: "medical" | "engineering" | "balanced";
  mode_label?: string;
  recommended_count: number;
  estimated_minutes: number;
  status: string;
  items: DailyPlanItem[];
};

export type QuestionType = "single" | "multiple" | "truefalse" | "numeric";

export type Choice = {
  choice_code: string;
  choice_text: string;
  display_order: number;
};

export type Question = {
  id: number;
  question_type: QuestionType;
  question_text: string;
  choices: Choice[];
  unit?: string | null;
  numeric_tolerance?: number | null;
  subject_name?: string | null;
  topic_name?: string | null;
  difficulty?: number;
  importance?: number;
};

export type AnswerPayload = {
  selected_codes: string[];
  numeric_answer: number | null;
  confidence: string;
  response_time_seconds: number;
  answer_mode: "daily";
};

export type AnswerResult = {
  is_correct: boolean;
  review_date: string;
  question: Question & {
    correct_codes?: string[];
    explanation_short?: string;
    explanation_standard?: string;
    explanation_detailed?: string;
    numeric_answer?: number | null;
    choices?: Array<Choice & { is_correct?: number; explanation?: string | null }>;
    choice_feedback?: Array<Choice & { is_correct?: boolean; selected?: boolean; explanation?: string | null; feedback_label?: string }>;
    learning_point?: string;
    answer_statistics?: {
      total_answers: number;
      correct_answers: number;
      correct_rate: number | null;
      label: string;
    };
  };
  related_questions?: Array<{
    id: number;
    question_text: string;
    question_type: QuestionType;
    importance: number;
    subject_name: string;
    topic_name: string;
    answered: number;
  }>;
};

export type LearningSummary = {
  total: number;
  correct: number;
  accuracy: number;
  avg_seconds: number;
  due_reviews: number;
};

export type DailyStatus = {
  date: string;
  status: "not_started" | "in_progress" | "completed";
  completed_count: number;
  total_count: number;
  estimated_minutes: number;
  streak_days: number;
  weekly: Array<{ date: string; completed: boolean }>;
  due_reviews: number;
  tomorrow_preview: { review_count: number; message: string };
  next_action: string;
};

export type ReviewItem = {
  review_id: number;
  scheduled_date: string;
  priority: number;
  status: string;
  question_id: number;
  question_text: string;
  question_type: QuestionType;
  subject_name: string;
  topic_name: string;
  completed: number;
  review_label: "今日" | "期限超過" | "今後" | "完了";
  reason: string;
};

export type ReviewQueue = {
  date: string;
  items: ReviewItem[];
  due_count: number;
  upcoming_count: number;
};

export type MasteryRow = {
  subject_name: string;
  topic_name: string;
  mastery_score: number;
  retention_score: number;
  total_answers: number;
  correct_answers: number;
  last_answered_at?: string | null;
};

export type SessionAnswer = {
  questionId: number;
  subjectName?: string | null;
  topicName?: string | null;
  isCorrect: boolean;
  reviewDate: string;
  seconds: number;
};

export type FeedbackPayload = {
  rating: number;
  category: string;
  message: string;
  page_url?: string;
  user_agent?: string;
};

export type StudyMode = "medical" | "engineering" | "balanced";

export type RadarSubject = {
  subject_code: string;
  subject_name: string;
  value: number;
  accuracy: number;
  mock_score?: number | null;
  answers: number;
};

export type ExamEvent = {
  id: number;
  event_type: "mock" | "past_exam" | "real_exam";
  title: string;
  event_date: string;
  status: string;
  memo?: string | null;
};

export type ScoreRecordPayload = {
  score_type: "mock" | "past_exam";
  title: string;
  taken_at: string;
  total_score: number;
  max_score: number;
  morning_score?: number | null;
  afternoon_score?: number | null;
  subject_scores: Record<string, number>;
  memo?: string;
};

export type StudyStrategy = {
  target_exam_date?: string | null;
  days_until_exam?: number | null;
  phase: "undecided" | "normal" | "push" | "final";
  phase_label: string;
  recommended_mode: StudyMode;
  recommendation: string;
  events: ExamEvent[];
  latest_score?: Record<string, unknown> | null;
  radar: RadarSubject[];
  weak_subjects: RadarSubject[];
  strong_subjects: RadarSubject[];
  weak_topics: MasteryRow[];
};

export type StudentNote = {
  id: number;
  user_id: number;
  title: string;
  content: string;
  source_type: string;
  created_at: string;
  updated_at: string;
  generated_question_count: number;
};

export type NoteExtractResult = {
  filename: string;
  content_type: string;
  source_type: string;
  text: string;
  warning?: string;
};

export type NoteQuestion = {
  id: number;
  note_id: number;
  user_id: number;
  question_type: "single";
  question_text: string;
  choices: Choice[];
  topic_code: string;
  status: string;
  created_at: string;
  answered?: boolean;
  explanation?: string;
  correct_code?: string;
  choice_feedback?: Array<Choice & { is_correct: boolean; selected?: boolean; explanation: string }>;
  learning_point?: string;
  answer_statistics?: {
    total_answers: number;
    correct_answers: number;
    correct_rate: number | null;
    label: string;
  };
};

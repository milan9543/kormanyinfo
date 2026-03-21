export interface Question {
  id: string;
  start_time: string;
  end_time: string;
  reporter: string;
  outlet: string;
  tags: string[];
  question: string;
  answer: string;
  criticism_percent: number;
  hostility_percent: number;
}

export interface OpeningStatement {
  speaker: string;
  start_time: string;
  end_time: string;
  tags: string[];
  summary: string;
}

export interface Speaker {
  name: string;
  role: string;
  position?: string;
}

export interface ConferenceMeta {
  title: string;
  date: string;
  youtube_url: string;
  youtube_video_id: string;
  duration: string;
  location: string;
}

export interface Conference {
  meta: ConferenceMeta;
  speakers: Speaker[];
  opening_statements: OpeningStatement[];
  questions: Question[];
}

export interface OutletStats {
  name: string;
  total_questions: number;
  avg_criticism: number;
  avg_hostility: number;
  conferences_attended: number;
}

export interface ReporterStats {
  name: string;
  outlet: string;
  total_questions: number;
  avg_criticism: number;
  avg_hostility: number;
  conferences_attended: number;
}

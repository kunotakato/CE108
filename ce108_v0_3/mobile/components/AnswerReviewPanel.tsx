import { VisualAidCard } from "@/components/VisualAid";
import type { AnswerResult } from "@/lib/types";

type Props = {
  detail: AnswerResult;
};

export function AnswerReviewPanel({ detail }: Props) {
  return (
    <section className="panel stack answer-result">
      <div className="result-heading">
        <span className="pill">解説と図解</span>
        <span className="pill">{detail.question.answer_statistics?.label || "回答済み"}</span>
      </div>
      <h2 className={detail.is_correct ? "correct" : "incorrect"}>{detail.is_correct ? "正解です" : "復習しましょう"}</h2>
      {detail.latest_answer ? (
        <p className="muted">
          回答日時: {detail.latest_answer.answered_at} / 自信度: {detail.latest_answer.confidence} / {detail.latest_answer.response_time_seconds}秒
        </p>
      ) : null}
      <p className="question-text">{detail.question.question_text}</p>
      {detail.question.learning_point ? (
        <>
          <div className="pill-row">
            <span className="pill">学習ポイント</span>
          </div>
          <p className="lead-small">{detail.question.learning_point}</p>
        </>
      ) : null}
      <VisualAidCard aid={detail.question.visual_aid} />
      <div className="explanation">
        <p>{detail.question.explanation_standard || detail.question.explanation_short || "解説は登録されていません。"}</p>
        {detail.review_date ? <p className="muted">復習日: {detail.review_date}</p> : null}
      </div>
      {detail.question.choice_feedback?.length ? (
        <div className="choice-feedback-list">
          {detail.question.choice_feedback.map((choice) => (
            <article
              className={`choice-feedback ${choice.is_correct ? "correct-choice" : choice.selected ? "selected-wrong-choice" : ""}`}
              key={choice.choice_code}
            >
              <div className="choice-feedback-header">
                <span className="choice-code">{choice.choice_code}</span>
                <span>{choice.feedback_label}</span>
              </div>
              <p className="choice-feedback-text">{choice.choice_text}</p>
              <p className="muted">{choice.explanation || "この選択肢の解説は登録されていません。"}</p>
            </article>
          ))}
        </div>
      ) : null}
      {detail.related_questions?.length ? (
        <div className="related-question-list">
          <h3>この知識を太くする問題</h3>
          {detail.related_questions.map((related) => (
            <article className="related-question" key={related.id}>
              <span>{related.topic_name}</span>
              <strong>{related.question_text}</strong>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

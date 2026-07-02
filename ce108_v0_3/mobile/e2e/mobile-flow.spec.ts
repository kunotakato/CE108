import { expect, test } from "@playwright/test";

const planItems = Array.from({ length: 5 }, (_, index) => ({
  id: index + 1,
  plan_id: 1,
  question_id: index + 1,
  item_type: index === 0 ? "復習" : "新規",
  display_order: index + 1,
  reason: "内部αテスト",
  question_text: `テスト問題 ${index + 1}`,
  question_type: index === 4 ? "numeric" : "single",
  importance: 3,
  subject_name: "基礎医学",
  topic_name: `分野${index + 1}`,
  completed: 0
}));

async function mockApi(page: import("@playwright/test").Page) {
  await page.route("**/api/auth/login", async (route) => {
    await route.fulfill({
      json: {
        access_token: "token",
        token_type: "bearer",
        user: { id: 1, email: "student@ce108.local", role: "student", display_name: "デモ学生" }
      }
    });
  });
  await page.route("**/api/study/today", async (route) => {
    await route.fulfill({ json: { id: 1, plan_date: "2026-07-01", recommended_count: 5, estimated_minutes: 8, status: "not_started", items: planItems } });
  });
  await page.route("**/api/study/summary", async (route) => {
    await route.fulfill({ json: { total: 10, correct: 7, accuracy: 70, avg_seconds: 32, due_reviews: 2 } });
  });
  await page.route("**/api/study/mastery?limit=3", async (route) => {
    await route.fulfill({ json: [{ subject_name: "基礎医学", topic_name: "解剖", mastery_score: 35, retention_score: 40, total_answers: 2, correct_answers: 1 }] });
  });
  await page.route("**/api/questions/**", async (route) => {
    const id = Number(route.request().url().match(/\/api\/questions\/(\d+)/)?.[1] ?? "0");
    if (route.request().method() === "POST") {
      await route.fulfill({
        json: {
          is_correct: true,
          review_date: "2026-07-08",
          question: { id, explanation_standard: "回答後だけ表示される解説です。" }
        }
      });
      return;
    }
    await route.fulfill({
      json: {
        id,
        question_type: id === 5 ? "numeric" : "single",
        question_text: `テスト問題 ${id}`,
        subject_name: "基礎医学",
        topic_name: `分野${id}`,
        choices: id === 5 ? [] : [{ choice_code: "1", choice_text: "選択肢A", display_order: 1 }]
      }
    });
  });
}

test("login to five-question completion", async ({ page }) => {
  await mockApi(page);
  await page.goto("/login");
  await page.getByRole("button", { name: "ログイン" }).click();
  await page.getByRole("button", { name: "ホームへ進む" }).click();
  await page.getByRole("link", { name: "今日の5問を始める" }).click();
  await page.waitForURL("**/study");

  for (let index = 1; index <= 5; index += 1) {
    await expect(page.getByText(`テスト問題 ${index}`)).toBeVisible();
    if (index === 5) {
      await page.getByPlaceholder("数値を入力").fill("42");
    } else {
      await page.getByRole("button", { name: /選択肢A/ }).click();
    }
    await page.getByRole("button", { name: "回答する" }).click();
    await expect(page.getByText("回答後だけ表示される解説です。")).toBeVisible();
    await expect(page.getByRole("button", { name: "回答済み" })).toBeDisabled();
    await page.getByRole("button", { name: index === 5 ? "結果を見る" : "次の問題へ" }).click();
  }

  await expect(page.getByRole("heading", { name: "完了しました。" })).toBeVisible();
});

for (const width of [320, 375, 390, 430]) {
  test(`no horizontal scroll at ${width}px`, async ({ page }) => {
    await mockApi(page);
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/login");
    await page.getByRole("button", { name: "ログイン" }).click();
    await page.getByRole("button", { name: "ホームへ進む" }).click();
    await expect(page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).resolves.toBe(true);
  });
}

test("shows retry UI when api fails", async ({ page }) => {
  await page.route("**/api/auth/login", async (route) => {
    await route.fulfill({ status: 401, json: { detail: "メールアドレスまたはパスワードが違います。" } });
  });
  await page.goto("/login");
  await page.getByRole("button", { name: "ログイン" }).click();
  await expect(page.locator(".state-view.error")).toContainText("メールアドレスまたはパスワードが違います。");
});

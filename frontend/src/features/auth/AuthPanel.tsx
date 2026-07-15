"use client";

import { useState } from "react";

import type { AuthSession } from "@/features/chat/types";
import { login, register } from "@/lib/api/authClient";

interface AuthPanelProps {
  visitorToken: string;
  onAuthenticated: (session: AuthSession) => Promise<void>;
  onClose: () => void;
}

export function AuthPanel({ visitorToken, onAuthenticated, onClose }: AuthPanelProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const session = mode === "register"
        ? await register({ visitorToken, email, password, nickname })
        : await login(email, password);
      await onAuthenticated(session);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "로그인 요청을 처리하지 못했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="auth-panel" aria-labelledby="auth-title">
      <div className="auth-heading">
        <div>
          <p className="eyebrow">취향 동기화</p>
          <h2 id="auth-title">{mode === "login" ? "다시 만나서 반가워요" : "취향을 계정에 저장하세요"}</h2>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="로그인 창 닫기">×</button>
      </div>

      <div className="auth-tabs" role="tablist" aria-label="인증 방식">
        <button type="button" role="tab" aria-selected={mode === "login"} onClick={() => setMode("login")}>로그인</button>
        <button type="button" role="tab" aria-selected={mode === "register"} onClick={() => setMode("register")}>회원가입</button>
      </div>

      <form className="auth-form" onSubmit={handleSubmit}>
        {mode === "register" && (
          <label>닉네임
            <input value={nickname} onChange={(event) => setNickname(event.target.value)} autoComplete="nickname" required minLength={1} maxLength={30} />
          </label>
        )}
        <label>이메일
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required maxLength={320} />
        </label>
        <label>비밀번호
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            required
            minLength={mode === "register" ? 12 : 1}
            maxLength={128}
          />
        </label>
        {mode === "register" && <p className="security-note">12자 이상으로 설정하세요. 비밀번호 원문은 저장하지 않습니다.</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "처리 중..." : mode === "login" ? "로그인" : "회원가입하고 취향 저장"}
        </button>
      </form>
    </section>
  );
}

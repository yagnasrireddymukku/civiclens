"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useAuth } from "@/components/auth";
import { Button, Input } from "@/components/primitives";
import { Link, useRouter } from "@/i18n/navigation";
import styles from "./page.module.css";

interface RegisterFormLabels {
  email: string;
  password: string;
  passwordHint: string;
  submit: string;
  loginPrompt: string;
  loginLink: string;
}

export function RegisterForm({ labels }: { labels: RegisterFormLabels }) {
  const { signUp } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    const result = await signUp(email, password);
    setLoading(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    router.push("/dashboard/tracking");
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      <Input
        type="email"
        autoComplete="email"
        label={labels.email}
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <Input
        type="password"
        autoComplete="new-password"
        label={labels.password}
        hint={labels.passwordHint}
        minLength={10}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />

      {error && (
        <p role="alert" className={styles.errorText}>
          {error}
        </p>
      )}

      <Button type="submit" loading={loading}>
        {labels.submit}
      </Button>

      <p className={styles.switchPrompt}>
        {labels.loginPrompt} <Link href="/login">{labels.loginLink}</Link>
      </p>
    </form>
  );
}

"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useAuth } from "@/components/auth";
import { Button, Input } from "@/components/primitives";
import { Link, useRouter } from "@/i18n/navigation";
import styles from "./page.module.css";

interface LoginFormLabels {
  email: string;
  password: string;
  submit: string;
  registerPrompt: string;
  registerLink: string;
}

export function LoginForm({ labels }: { labels: LoginFormLabels }) {
  const { signIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    const result = await signIn(email, password);
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
        autoComplete="current-password"
        label={labels.password}
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
        {labels.registerPrompt} <Link href="/register">{labels.registerLink}</Link>
      </p>
    </form>
  );
}

"use client";

import { SignUp } from "@clerk/nextjs";
import AuthShell from "@/components/auth-shell";

export default function SignUpPage() {
  return (
    <AuthShell>
      <SignUp appearance={{ elements: { cardBox: "shadow-[0_8px_30px_rgb(23_23_28/0.06)] border border-[var(--line)] rounded-[18px]" } }} />
    </AuthShell>
  );
}

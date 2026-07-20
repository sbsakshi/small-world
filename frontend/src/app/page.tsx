"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useCurrentUser } from "@/lib/useCurrentUser";

export default function Home() {
  const router = useRouter();
  const { user, status } = useCurrentUser();

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/login");
    if (status === "authenticated" && user) {
      router.replace(user.user_type === "volunteer" ? "/volunteer" : "/cities");
    }
  }, [status, user, router]);

  return <main style={{ minHeight: "100vh", background: "var(--canvas)" }} />;
}

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useCurrentUser } from "./useCurrentUser";
import type { CurrentUser } from "./api";

type Allow = "staff" | "volunteer" | "any";

export function useRequireAuth(allow: Allow = "any"): { user: CurrentUser | null; ready: boolean } {
  const router = useRouter();
  const { user, status } = useCurrentUser();

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/login");
  }, [status, router]);

  useEffect(() => {
    if (status !== "authenticated" || !user) return;
    if (allow === "staff" && user.user_type !== "staff") router.replace("/volunteer");
    if (allow === "volunteer" && user.user_type !== "volunteer") router.replace("/cities");
  }, [status, user, allow, router]);

  const ready = status === "authenticated" && !!user && (allow === "any" || user.user_type === allow);
  return { user, ready };
}

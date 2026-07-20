"use client";

import { useEffect, useState } from "react";
import { me, type CurrentUser } from "./api";

type Status = "loading" | "authenticated" | "unauthenticated";

export function useCurrentUser(): { user: CurrentUser | null; status: Status } {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    let cancelled = false;
    me()
      .then((u) => {
        if (!cancelled) {
          setUser(u);
          setStatus("authenticated");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setUser(null);
          setStatus("unauthenticated");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { user, status };
}

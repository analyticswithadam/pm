"use client";

import { useEffect, useSyncExternalStore } from "react";
import { useRouter, usePathname } from "next/navigation";

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

const getToken = () => localStorage.getItem("token");
const getTokenServer = () => null;

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const pathname = usePathname();

  // useSyncExternalStore avoids hydration mismatch: server uses null, client reads localStorage
  const token = useSyncExternalStore(subscribe, getToken, getTokenServer);
  const isAuthenticated = typeof token === "string" && token.length > 0;

  useEffect(() => {
    if (isAuthenticated && pathname === "/login") {
      router.replace("/");
    } else if (!isAuthenticated && pathname !== "/login") {
      router.replace("/login");
    }
  }, [isAuthenticated, pathname, router]);

  if (!isAuthenticated && pathname !== "/login") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--surface-strong)]">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-[var(--stroke)] border-t-[var(--primary-blue)]" />
      </div>
    );
  }

  return <>{children}</>;
};

"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    // Check localStorage for the fake auth token
    const token = localStorage.getItem("auth");
    
    if (token === "true") {
      setIsAuthenticated(true);
      // If they are on the login page but already authenticated, send them to the board
      if (pathname === "/login") {
        router.replace("/");
      }
    } else {
      setIsAuthenticated(false);
      // If they are not authenticated and not on the login page, send them to login
      if (pathname !== "/login") {
        router.replace("/login");
      }
    }
  }, [pathname, router]);

  // While checking auth on mount, or if unauthenticated and redirecting, show a loader
  if (isAuthenticated === null || (isAuthenticated === false && pathname !== "/login")) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--surface-strong)]">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-[var(--stroke)] border-t-[var(--primary-blue)]" />
      </div>
    );
  }

  // Render children normally if authenticated or if on the login page
  return <>{children}</>;
};

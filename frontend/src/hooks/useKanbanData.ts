import { useState, useEffect, useCallback, useRef } from "react";
import { BoardData } from "../lib/kanban";

function getAuthHeader(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function useKanbanData() {
  const [board, setBoard] = useState<BoardData>({ columns: [], cards: {} });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const previousBoardRef = useRef<BoardData>({ columns: [], cards: {} });

  const fetchBoard = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/board", { headers: getAuthHeader() });
      if (!res.ok) {
        throw new Error("Failed to fetch board data");
      }
      const data: BoardData = await res.json();
      setBoard({ columns: data.columns || [], cards: data.cards || {} });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load board");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBoard();
  }, [fetchBoard]);

  const syncBoard = async (newBoard: BoardData) => {
    previousBoardRef.current = board;
    setBoard(newBoard);
    setSyncError(null);

    try {
      const res = await fetch("/api/board", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader(),
        },
        body: JSON.stringify(newBoard),
      });
      if (!res.ok) {
        throw new Error("Failed to sync board data");
      }
    } catch (err: unknown) {
      setBoard(previousBoardRef.current);
      setSyncError(err instanceof Error ? err.message : "Sync failed — your last change was not saved");
    }
  };

  return { board, setBoard, loading, error, syncError, syncBoard, fetchBoard };
}

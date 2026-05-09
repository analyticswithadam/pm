import { useState, useEffect, useCallback } from "react";
import { BoardData } from "../lib/kanban";

export function useKanbanData() {
  const [board, setBoard] = useState<BoardData>({ columns: [], cards: {} });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBoard = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/board");
      if (!res.ok) {
        throw new Error("Failed to fetch board data");
      }
      const data: BoardData = await res.json();
      setBoard({ columns: data.columns || [], cards: data.cards || {} });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBoard();
  }, [fetchBoard]);

  const syncBoard = async (newBoard: BoardData) => {
    setBoard(newBoard);
    
    try {
      const res = await fetch("/api/board", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(newBoard),
      });
      if (!res.ok) {
        throw new Error("Failed to sync board data");
      }
    } catch (err: any) {
      console.error("Sync error:", err);
    }
  };

  return { board, setBoard, loading, error, syncBoard };
}

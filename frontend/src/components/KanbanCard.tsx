import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import { Trash2 } from "lucide-react";
import type { Card } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
};

export const KanbanCard = ({ card, onDelete }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "rounded-2xl border border-transparent bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        isDragging && "opacity-60 shadow-[0_18_32px_rgba(3,33,71,0.16)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 overflow-hidden">
          <h4 className="truncate font-display text-sm font-semibold text-[var(--navy-dark)]">
            {card.title}
          </h4>
          <p className="mt-1 text-xs leading-5 text-[var(--gray-text)] line-clamp-2">
            {card.details}
          </p>
        </div>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(card.id);
          }}
          className="group/btn flex h-6 w-6 items-center justify-center rounded-md text-[var(--gray-text)] transition-colors hover:bg-red-50 hover:text-red-500"
          aria-label={`Delete ${card.title}`}
        >
          <Trash2 size={14} className="opacity-40 transition-opacity group-hover/btn:opacity-100" />
        </button>
      </div>
    </article>
  );
};

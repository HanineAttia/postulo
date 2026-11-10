import {
  closestCenter,
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  ArrowDown,
  ArrowUp,
  ChevronDown,
  CircleAlert,
  GripVertical,
  Plus,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import {
  type FieldArrayPath,
  get,
  useFieldArray,
  useFormContext,
  useFormState,
  useWatch,
} from "react-hook-form";
import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useDynamicT } from "@/lib/i18nKey";
import { cn } from "@/lib/utils";

import { FieldGrid } from "./fields";
import { type CareerProfile, emptyItem, type ItemSection } from "./schema";
import { SECTION_FIELDS, SECTION_TITLE_FIELDS } from "./sections";

/** A list section (experiences, projects...): collapsible cards, drag and drop, add, delete. */
export function ItemSectionEditor({ section }: { section: ItemSection }) {
  const td = useDynamicT();
  const { control } = useFormContext<CareerProfile>();
  const { fields, append, remove, move } = useFieldArray({
    control,
    name: section as FieldArrayPath<CareerProfile>,
    keyName: "fieldKey",
  });
  const [open, setOpen] = useState<Set<string>>(() => new Set());
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const keys = fields.map((field) => field.fieldKey);

  // Open cards are tracked by item id (stable, unlike the array index).
  const toggle = (itemId: string) =>
    setOpen((previous) => {
      const next = new Set(previous);
      if (next.has(itemId)) next.delete(itemId);
      else next.add(itemId);
      return next;
    });

  const add = () => {
    const item = emptyItem(section);
    append(item as never, { shouldFocus: false });
    setOpen((previous) => new Set(previous).add(item.id));
  };

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    move(keys.indexOf(String(active.id)), keys.indexOf(String(over.id)));
  };

  const titleId = `section-${section}-title`;
  return (
    <Card aria-labelledby={titleId}>
      <CardHeader className="flex-row items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <CardTitle id={titleId}>{td(`profile.sections.${section}.title`)}</CardTitle>
          <CardDescription>{td(`profile.sections.${section}.description`)}</CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={add}>
          <Plus aria-hidden="true" />
          {td(`profile.sections.${section}.add`)}
        </Button>
      </CardHeader>
      <CardContent>
        {fields.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border px-4 py-6 text-center text-sm text-muted">
            {td(`profile.sections.${section}.empty`)}
          </p>
        ) : (
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
            <SortableContext items={keys} strategy={verticalListSortingStrategy}>
              <ol className="flex flex-col gap-2" aria-label={td(`profile.sections.${section}.title`)}>
                {fields.map((field, index) => {
                  const itemId = (field as unknown as { id: string }).id;
                  return (
                    <SortableItemCard
                      key={field.fieldKey}
                      sortId={field.fieldKey}
                      section={section}
                      index={index}
                      count={fields.length}
                      open={open.has(itemId)}
                      onToggle={() => toggle(itemId)}
                      onMove={(to) => move(index, to)}
                      onRemove={() => remove(index)}
                    />
                  );
                })}
              </ol>
            </SortableContext>
          </DndContext>
        )}
      </CardContent>
    </Card>
  );
}

interface SortableItemCardProps {
  sortId: string;
  section: ItemSection;
  index: number;
  count: number;
  open: boolean;
  onToggle: () => void;
  onMove: (to: number) => void;
  onRemove: () => void;
}

function SortableItemCard({
  sortId,
  section,
  index,
  count,
  open,
  onToggle,
  onMove,
  onRemove,
}: SortableItemCardProps) {
  const { t } = useTranslation();
  const { control } = useFormContext<CareerProfile>();
  const path = `${section}.${index}`;
  const item = useWatch({ control, name: path as never }) as Record<string, unknown> | undefined;
  const { errors } = useFormState({ control, name: path as never });
  const hasError = Boolean(get(errors, path));
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } =
    useSortable({ id: sortId });

  const parts = SECTION_TITLE_FIELDS[section]
    .map((name) => item?.[name])
    .filter((value): value is string => typeof value === "string" && value.trim() !== "");
  const title = parts.join(" · ") || t("profile.untitled");
  const dates = [item?.start ?? item?.date, item?.end]
    .filter((value): value is string => typeof value === "string" && value !== "")
    .join(" – ");
  const bodyId = `item-${sortId}-body`;

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "rounded-lg border bg-surface-raised",
        hasError ? "border-danger" : "border-border",
        isDragging && "relative z-10 shadow-md",
      )}
      data-testid={`${section}-item`}
    >
      <div className="flex items-center gap-1 px-2 py-1.5">
        <button
          type="button"
          ref={setActivatorNodeRef}
          className="flex size-8 cursor-grab items-center justify-center rounded-md text-muted hover:bg-surface focus-visible:outline-2 focus-visible:outline-ring active:cursor-grabbing"
          aria-label={t("profile.dragHandle", { title })}
          {...attributes}
          {...listeners}
        >
          <GripVertical className="size-4" aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={open}
          aria-controls={bodyId}
          className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-1 text-left hover:bg-surface focus-visible:outline-2 focus-visible:outline-ring"
        >
          <ChevronDown
            className={cn("size-4 shrink-0 text-muted transition-transform", !open && "-rotate-90")}
            aria-hidden="true"
          />
          <span className="truncate text-sm font-medium text-ink">{title}</span>
          {dates ? <span className="tabular shrink-0 text-xs text-muted">{dates}</span> : null}
          {hasError ? (
            <Badge variant="danger" className="ml-auto">
              <CircleAlert aria-hidden="true" />
              {t("profile.hasErrors")}
            </Badge>
          ) : null}
        </button>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onMove(index - 1)}
          disabled={index === 0}
          aria-label={t("profile.moveUp", { title })}
        >
          <ArrowUp aria-hidden="true" />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onMove(index + 1)}
          disabled={index === count - 1}
          aria-label={t("profile.moveDown", { title })}
        >
          <ArrowDown aria-hidden="true" />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onRemove}
          aria-label={t("profile.remove", { title })}
          className="text-muted hover:text-danger"
        >
          <Trash2 aria-hidden="true" />
        </Button>
      </div>
      {/* Kept mounted when closed so validation still reaches every field. */}
      <div id={bodyId} hidden={!open} className="border-t border-border p-4">
        <FieldGrid
          prefix={path}
          specs={SECTION_FIELDS[section]}
          labelPrefix={`profile.fields.${section}`}
        />
      </div>
    </li>
  );
}

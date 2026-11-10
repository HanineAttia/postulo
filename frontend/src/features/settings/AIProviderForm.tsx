import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CircleAlert,
  CircleCheck,
  FlaskConical,
  KeyRound,
  LoaderCircle,
  PlugZap,
  Save,
  Terminal,
  Trash2,
  type LucideIcon,
  Cloud,
  Server,
} from "lucide-react";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useLLMStatus } from "@/features/llm/useLLMStatus";
import { api, type ConnectionTest, type ProviderName, type SettingsRead } from "@/lib/api";
import { cn } from "@/lib/utils";

import { toSettings, useSaveSettings, useSettings } from "./useSettings";

const PROVIDER_ICON: Record<ProviderName, LucideIcon> = {
  mock: FlaskConical,
  anthropic_api: Cloud,
  claude_code_cli: Terminal,
  openai_compatible: Server,
};
const ORDER: ProviderName[] = ["mock", "anthropic_api", "claude_code_cli", "openai_compatible"];

/** Choose the AI provider, its model and key, and test the connection (SPEC 12.3). */
export function AIProviderForm() {
  const settings = useSettings();
  if (settings.isPending) return <Skeleton className="h-64 w-full" />;
  if (settings.isError) return <ServerError />;
  return <AIProviderFormLoaded initial={settings.data} />;
}

function ServerError() {
  const { t } = useTranslation();
  return (
    <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">
      {t("errors.server")}
    </p>
  );
}

function AIProviderFormLoaded({ initial }: { initial: SettingsRead }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const providers = useQuery({ queryKey: ["llm-providers"], queryFn: api.providers });
  const status = useLLMStatus();
  const save = useSaveSettings();
  const [provider, setProvider] = useState<ProviderName>(initial.ai.provider);
  const [model, setModel] = useState(initial.ai.model ?? "");
  const [timeoutSeconds, setTimeoutSeconds] = useState(initial.ai.timeout_seconds);
  const [result, setResult] = useState<ConnectionTest | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const groupId = useId();
  const info = providers.data?.find((p) => p.name === provider);
  const dirty =
    provider !== initial.ai.provider ||
    (model.trim() || null) !== initial.ai.model ||
    timeoutSeconds !== initial.ai.timeout_seconds;

  const persist = async () => {
    const saved = await save.mutateAsync({
      ...toSettings(initial),
      ai: { provider, model: model.trim() || null, timeout_seconds: timeoutSeconds },
    });
    return saved;
  };

  const test = useMutation({
    mutationFn: async () => {
      if (dirty) await persist();
      return api.testConnection();
    },
    onSuccess: (value) => {
      setResult(value);
      setShowDetail(false);
      void queryClient.invalidateQueries({ queryKey: ["llm-status"] });
    },
    onError: (error) => toast.error(error.message || t("errors.generic")),
  });

  const onSave = () =>
    void persist()
      .then(() => toast.success(t("settings.ai.saved")))
      .catch((error: Error) => toast.error(error.message || t("errors.generic")));

  return (
    <div className="flex flex-col gap-6">
      <fieldset>
        <legend className="mb-3 text-sm font-medium text-ink">{t("settings.ai.providerLabel")}</legend>
        <div className="grid gap-2 sm:grid-cols-2">
          {ORDER.map((name) => {
            const Icon = PROVIDER_ICON[name];
            const providerInfo = providers.data?.find((p) => p.name === name);
            const disabled = providerInfo ? !providerInfo.implemented : name === "openai_compatible";
            const id = `${groupId}-${name}`;
            return (
              <label
                key={name}
                htmlFor={id}
                className={cn(
                  "flex gap-3 rounded-lg border p-3 text-sm has-focus-visible:outline-2 has-focus-visible:outline-ring",
                  provider === name ? "border-primary bg-primary-soft" : "border-border",
                  disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
                )}
              >
                <input
                  id={id}
                  type="radio"
                  name={groupId}
                  value={name}
                  checked={provider === name}
                  disabled={disabled}
                  onChange={() => {
                    setProvider(name);
                    setModel("");
                    setResult(null);
                  }}
                  className="sr-only"
                />
                <Icon className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
                <span className="flex flex-col gap-1">
                  <span className="flex flex-wrap items-center gap-2 font-medium text-ink">
                    {t(`providers.${name}`)}
                    {providerInfo?.personal_use_only ? (
                      <Badge variant="warning">{t("settings.ai.personalUse")}</Badge>
                    ) : null}
                    {disabled ? <Badge>{t("pages.comingSoon", { phase: 6 })}</Badge> : null}
                  </span>
                  <span className="text-muted">{t(`settings.ai.descriptions.${name}`)}</span>
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {provider === "claude_code_cli" ? (
        <div className="flex gap-2 rounded-lg bg-warning-soft px-4 py-3 text-sm text-warning" role="note">
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <p>{t("settings.ai.termsNote")}</p>
        </div>
      ) : null}

      {provider !== "mock" ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            id={`${groupId}-model`}
            label={t("settings.ai.model")}
            hint={
              info?.default_model
                ? t("settings.ai.modelDefault", { model: info.default_model })
                : t("settings.ai.modelCliHint")
            }
          >
            <Input
              id={`${groupId}-model`}
              list={`${groupId}-models`}
              value={model}
              placeholder={info?.default_model ?? ""}
              onChange={(event) => setModel(event.target.value)}
              aria-describedby={`${groupId}-model-hint`}
              autoComplete="off"
            />
            <datalist id={`${groupId}-models`}>
              {(info?.suggested_models ?? []).map((value) => (
                <option key={value} value={value} />
              ))}
            </datalist>
          </Field>
          <Field id={`${groupId}-timeout`} label={t("settings.ai.timeout")} hint={t("settings.ai.timeoutHint")}>
            <Input
              id={`${groupId}-timeout`}
              type="number"
              min={10}
              max={1800}
              value={timeoutSeconds}
              onChange={(event) => setTimeoutSeconds(Number(event.target.value) || 300)}
              aria-describedby={`${groupId}-timeout-hint`}
            />
          </Field>
        </div>
      ) : null}

      {provider === "anthropic_api" ? (
        <ApiKeyField hasKey={status.data?.has_api_key ?? false} />
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={() => test.mutate()} disabled={test.isPending || save.isPending}>
          {test.isPending ? (
            <LoaderCircle className="animate-spin" aria-hidden="true" />
          ) : (
            <PlugZap aria-hidden="true" />
          )}
          {t("settings.ai.test")}
        </Button>
        <Button variant="outline" onClick={onSave} disabled={!dirty || save.isPending}>
          <Save aria-hidden="true" />
          {t("settings.ai.save")}
        </Button>
        {provider !== "mock" ? (
          <span className="text-xs text-muted">{t("settings.ai.testCost")}</span>
        ) : null}
      </div>

      <div aria-live="polite">
        {result ? (
          <div
            className={cn(
              "flex flex-col gap-1 rounded-lg px-4 py-3 text-sm",
              result.ok ? "bg-success-soft text-success" : "bg-danger-soft text-danger",
            )}
            data-testid="connection-result"
          >
            <p className="flex items-center gap-2 font-medium">
              {result.ok ? (
                <CircleCheck className="size-4" aria-hidden="true" />
              ) : (
                <CircleAlert className="size-4" aria-hidden="true" />
              )}
              {result.message}
              {result.ok ? (
                <span className="tabular font-normal">
                  {t("settings.ai.duration", { seconds: (result.duration_ms / 1000).toFixed(1) })}
                </span>
              ) : null}
            </p>
            {result.detail ? (
              <>
                <button
                  type="button"
                  onClick={() => setShowDetail((value) => !value)}
                  aria-expanded={showDetail}
                  className="self-start text-xs underline"
                >
                  {t("errors.details")}
                </button>
                {showDetail ? (
                  <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded bg-surface-raised p-2 text-xs text-ink">
                    {result.detail}
                  </pre>
                ) : null}
              </>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ApiKeyField({ hasKey }: { hasKey: boolean }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const id = useId();
  const [value, setValue] = useState("");
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["llm-status"] });
  const saveKey = useMutation({
    mutationFn: api.saveApiKey,
    onSuccess: () => {
      setValue("");
      refresh();
      toast.success(t("settings.ai.keySaved"));
    },
    onError: (error) => toast.error(error.message || t("errors.generic")),
  });
  const deleteKey = useMutation({ mutationFn: api.deleteApiKey, onSuccess: refresh });

  return (
    <div className="flex flex-col gap-2">
      <Field id={id} label={t("settings.ai.apiKey")} hint={t("settings.ai.apiKeyHint")}>
        <div className="flex gap-2">
          <Input
            id={id}
            type="password"
            autoComplete="off"
            spellCheck={false}
            value={value}
            placeholder={hasKey ? "••••••••••••" : "sk-ant-..."}
            onChange={(event) => setValue(event.target.value)}
            aria-describedby={`${id}-hint`}
          />
          <Button
            variant="outline"
            onClick={() => saveKey.mutate(value.trim())}
            disabled={value.trim().length < 10 || saveKey.isPending}
          >
            <KeyRound aria-hidden="true" />
            {t("settings.ai.saveKey")}
          </Button>
        </div>
      </Field>
      {hasKey ? (
        <div className="flex items-center gap-2 text-sm text-success">
          <CircleCheck className="size-4" aria-hidden="true" />
          {t("settings.ai.keyStored")}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => deleteKey.mutate()}
            disabled={deleteKey.isPending}
          >
            <Trash2 aria-hidden="true" />
            {t("settings.ai.deleteKey")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

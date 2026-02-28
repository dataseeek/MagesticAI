import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AnthropicIcon } from '../../icons/AnthropicIcon';
import { OpenAIIcon } from '../../icons/OpenAIIcon';
import { GeminiIcon } from '../../icons/GeminiIcon';
import { OllamaIcon } from '../../icons/OllamaIcon';
import { apiRequest } from '@/lib/api-client';
import type { AppSettings } from '@/shared/types/settings';

interface QALLMProviderSettingsProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
}

type QaLlmProvider = NonNullable<AppSettings['qaLlmProvider']>;

const QA_LLM_PROVIDERS: {
  value: QaLlmProvider;
  labelKey: string;
  icon: React.ReactNode;
}[] = [
  {
    value: 'claude',
    labelKey: 'sections.llmProvider.qaProvider.providers.claude',
    icon: <AnthropicIcon className="h-3.5 w-3.5 shrink-0" />,
  },
  {
    value: 'codex',
    labelKey: 'sections.llmProvider.qaProvider.providers.codex',
    icon: <OpenAIIcon className="h-3.5 w-3.5 shrink-0" />,
  },
  {
    value: 'gemini',
    labelKey: 'sections.llmProvider.qaProvider.providers.gemini',
    icon: <GeminiIcon className="h-3.5 w-3.5 shrink-0" />,
  },
  {
    value: 'ollama',
    labelKey: 'sections.llmProvider.qaProvider.providers.ollama',
    icon: <OllamaIcon className="h-3.5 w-3.5 shrink-0" />,
  },
];

export function QALLMProviderSettings({ settings, onSettingsChange }: QALLMProviderSettingsProps) {
  const { t } = useTranslation('settings');

  const [currentProvider, setCurrentProvider] = useState<QaLlmProvider>(
    settings.qaLlmProvider ?? 'claude'
  );
  const [isSaving, setIsSaving] = useState(false);

  // Read on mount: fetch the authoritative value from the dedicated endpoint
  useEffect(() => {
    async function fetchProvider() {
      try {
        const result = await apiRequest<{ qaLlmProvider: QaLlmProvider }>('/settings/qa-llm-provider');
        if (result.success && result.data?.qaLlmProvider) {
          const fetched = result.data.qaLlmProvider;
          setCurrentProvider(fetched);
          // Sync into parent settings if the fetched value differs
          if (fetched !== settings.qaLlmProvider) {
            onSettingsChange({ ...settings, qaLlmProvider: fetched });
          }
        }
      } catch {
        // Fall back to the value supplied by parent settings
      }
    }
    fetchProvider();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Persist on change: immediately write to the dedicated API endpoint
  const handleProviderChange = async (value: string) => {
    const provider = value as QaLlmProvider;

    // Optimistic local update
    setCurrentProvider(provider);
    onSettingsChange({ ...settings, qaLlmProvider: provider });

    setIsSaving(true);
    try {
      await apiRequest('/settings/qa-llm-provider', {
        method: 'PUT',
        body: { qaLlmProvider: provider },
      });
    } catch {
      // Persist failure is non-fatal; parent state still reflects the choice
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="qa-llm-provider-select">
          {t('sections.llmProvider.qaProvider.providerLabel')}
        </Label>
        <p className="text-xs text-muted-foreground">
          {t('sections.llmProvider.qaProvider.providerDescription')}
        </p>
        <Select
          value={currentProvider}
          onValueChange={handleProviderChange}
          disabled={isSaving}
        >
          <SelectTrigger id="qa-llm-provider-select" className="w-full max-w-md">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {QA_LLM_PROVIDERS.map(({ value, labelKey, icon }) => (
              <SelectItem key={value} value={value}>
                <div className="flex items-center gap-2">
                  {icon}
                  <span>{t(labelKey)}</span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {currentProvider !== 'claude' && (
        <p className="text-xs text-muted-foreground rounded-md border border-border bg-muted/30 px-3 py-2">
          {t('sections.llmProvider.qaProvider.cliNote')}
        </p>
      )}
    </div>
  );
}

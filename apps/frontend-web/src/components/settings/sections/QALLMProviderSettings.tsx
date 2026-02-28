import { useTranslation } from 'react-i18next';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AnthropicIcon } from '../../icons/AnthropicIcon';
import { OpenAIIcon } from '../../icons/OpenAIIcon';
import { GeminiIcon } from '../../icons/GeminiIcon';
import { OllamaIcon } from '../../icons/OllamaIcon';
import type { AppSettings } from '@/shared/types/settings';

interface QALLMProviderSettingsProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
}

const QA_LLM_PROVIDERS: {
  value: NonNullable<AppSettings['qaLlmProvider']>;
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

  const currentProvider = settings.qaLlmProvider ?? 'claude';

  const handleProviderChange = (value: string) => {
    onSettingsChange({
      ...settings,
      qaLlmProvider: value as NonNullable<AppSettings['qaLlmProvider']>,
    });
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
        <Select value={currentProvider} onValueChange={handleProviderChange}>
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

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { RefreshCw } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { fetchOpenAICompatibleModels } from '@/shared/constants';
import type { AppSettings } from '@/shared/types/settings';

interface QAProviderSettingsProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
}

export function QAProviderSettings({ settings, onSettingsChange }: QAProviderSettingsProps) {
  const { t } = useTranslation('settings');
  const [openAICompatModels, setOpenAICompatModels] = useState<{ value: string; label: string }[]>([]);
  const [isFetchingModels, setIsFetchingModels] = useState(false);

  const qaProvider = settings.qaLlmProvider || 'claude';
  // Default base URL: qaOpenaiCompatBaseUrl > llmOpenaiBaseUrl > ''
  const effectiveBaseUrl = settings.qaOpenaiCompatBaseUrl || settings.llmOpenaiBaseUrl || '';

  const loadOpenAICompatModels = async (baseUrl?: string) => {
    setIsFetchingModels(true);
    try {
      const models = await fetchOpenAICompatibleModels(baseUrl || effectiveBaseUrl || undefined);
      setOpenAICompatModels(models);
    } finally {
      setIsFetchingModels(false);
    }
  };

  useEffect(() => {
    if (qaProvider === 'openai_compat') {
      loadOpenAICompatModels();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qaProvider, effectiveBaseUrl]);

  return (
    <div className="space-y-4">
      {/* Provider selector */}
      <div className="space-y-2">
        <Label>{t('sections.llmProvider.qaProvider.providerLabel')}</Label>
        <p className="text-sm text-muted-foreground">
          {t('sections.llmProvider.qaProvider.providerDescription')}
        </p>
        <Select
          value={qaProvider}
          onValueChange={(value) =>
            onSettingsChange({
              ...settings,
              qaLlmProvider: value as AppSettings['qaLlmProvider'],
            })
          }
        >
          <SelectTrigger className="w-full max-w-md">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="claude">
              {t('sections.llmProvider.qaProvider.providers.claude')}
            </SelectItem>
            <SelectItem value="codex">
              {t('sections.llmProvider.qaProvider.providers.codex')}
            </SelectItem>
            <SelectItem value="gemini">
              {t('sections.llmProvider.qaProvider.providers.gemini')}
            </SelectItem>
            <SelectItem value="ollama">
              {t('sections.llmProvider.qaProvider.providers.ollama')}
            </SelectItem>
            <SelectItem value="openai_compat">
              {t('sections.llmProvider.qaProvider.providers.openai_compat')}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* CLI note for CLI-based providers */}
      {(qaProvider === 'codex' || qaProvider === 'gemini') && (
        <p className="text-sm text-muted-foreground rounded-md bg-muted/50 px-3 py-2">
          {t('sections.llmProvider.qaProvider.cliNote')}
        </p>
      )}

      {/* OpenAI Compatible config inputs */}
      {qaProvider === 'openai_compat' && (
        <div className="space-y-4 border-l-2 border-primary/20 pl-4">
          {/* Base URL input */}
          <div className="space-y-2">
            <Label>
              {t('sections.llmProvider.qaProvider.openaiCompatBaseUrlLabel')}
            </Label>
            <p className="text-sm text-muted-foreground">
              {t('sections.llmProvider.qaProvider.openaiCompatBaseUrlDescription')}
            </p>
            <Input
              value={settings.qaOpenaiCompatBaseUrl || settings.llmOpenaiBaseUrl || ''}
              onChange={(e) =>
                onSettingsChange({ ...settings, qaOpenaiCompatBaseUrl: e.target.value })
              }
              placeholder="http://localhost:1234"
              className="max-w-md"
            />
          </div>

          {/* Model dropdown */}
          <div className="space-y-2">
            <div className="flex items-center justify-between max-w-md">
              <Label>{t('sections.llmProvider.qaProvider.openaiCompatModelLabel')}</Label>
              <Button
                size="sm"
                variant="outline"
                onClick={() => loadOpenAICompatModels()}
                disabled={isFetchingModels}
                className="gap-1.5"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isFetchingModels ? 'animate-spin' : ''}`} />
                {t('sections.llmProvider.qaProvider.refreshModels')}
              </Button>
            </div>
            <Select
              value={settings.qaOpenaiCompatModel || ''}
              onValueChange={(value) =>
                onSettingsChange({ ...settings, qaOpenaiCompatModel: value })
              }
            >
              <SelectTrigger className="w-full max-w-md">
                <SelectValue
                  placeholder={t('sections.llmProvider.qaProvider.openaiCompatModelPlaceholder')}
                />
              </SelectTrigger>
              <SelectContent>
                {openAICompatModels.length > 0 ? (
                  openAICompatModels.map((model) => (
                    <SelectItem key={model.value} value={model.value}>
                      {model.label}
                    </SelectItem>
                  ))
                ) : settings.qaOpenaiCompatModel ? (
                  <SelectItem value={settings.qaOpenaiCompatModel}>
                    {settings.qaOpenaiCompatModel}
                  </SelectItem>
                ) : (
                  <SelectItem value="_no_models" disabled>
                    {t('sections.llmProvider.qaProvider.openaiCompatNoModels')}
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}
    </div>
  );
}

import { Bot, Info } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useTranslation } from 'react-i18next';
import { useState, useEffect } from 'react';
import type { AppSettings } from '@/shared/types/settings';
import { apiRequest } from '@/lib/api-client';

interface LLMProviderSettingsProps {
  settings: AppSettings;
  onSettingsChange: (settings: Partial<AppSettings>) => void;
}

export function LLMProviderSettings({ settings, onSettingsChange }: LLMProviderSettingsProps) {
  const { t } = useTranslation(['settings', 'common']);
  const [ollamaModels, setOllamaModels] = useState<any[]>([]);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<{type: 'success'|'error', message: string} | null>(null);

  const provider = settings.llmProvider || 'ollama';

  // Load Ollama models
  useEffect(() => {
    if (provider === 'ollama') {
      fetchOllamaModels();
    }
  }, [provider, settings.llmOllamaBaseUrl]);

  const fetchOllamaModels = async () => {
    try {
      const result = await apiRequest<{ models: any[] }>(
        `/settings/ollama/models?ollamaBaseUrl=${encodeURIComponent(settings.llmOllamaBaseUrl || 'http://localhost:11434')}`
      );
      if (result.success && result.data) {
        setOllamaModels(result.data.models);
      }
    } catch (error) {
      console.error('Failed to fetch Ollama models:', error);
    }
  };

  const testConnection = async () => {
    setIsTestingConnection(true);
    setConnectionStatus(null);

    try {
      if (provider === 'ollama') {
        const result = await apiRequest<{ message: string }>('/settings/ollama/test', {
          method: 'POST',
          body: {
            ollamaBaseUrl: settings.llmOllamaBaseUrl || 'http://localhost:11434',
            modelName: settings.llmOllamaModel || 'qwen3-30b-local:latest'
          }
        });

        setConnectionStatus({
          type: result.success ? 'success' : 'error',
          message: result.success
            ? ((result.data as any)?.message || (result as any).message || 'Connected!')
            : (result.error || 'Connection failed')
        });
      }
      // Add Anthropic/OpenAI test logic here if needed
    } catch (error) {
      setConnectionStatus({ type: 'error', message: String(error) });
    } finally {
      setIsTestingConnection(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Bot className="h-5 w-5" />
        <h3 className="text-lg font-semibold">{t('settings:sections.llmProvider.title')}</h3>
      </div>

      <p className="text-sm text-muted-foreground">
        {t('settings:sections.llmProvider.description')}
      </p>

      {/* Future Implementation Notice */}
      <div className="flex items-start gap-2 p-3 rounded-md bg-info/10 border border-info/20">
        <Info className="h-4 w-4 text-info shrink-0 mt-0.5" />
        <p className="text-sm text-muted-foreground">
          {t('settings:sections.llmProvider.futureNotice', 'This feature is planned for future implementation. Settings are saved but not yet active.')}
        </p>
      </div>

      {/* Provider Selection */}
      <div className="space-y-2">
        <Label>{t('settings:sections.llmProvider.providerLabel')}</Label>
        <Select
          value={provider}
          onValueChange={(value) => onSettingsChange({ llmProvider: value as any })}
        >
          <SelectTrigger className="w-full max-w-md">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ollama">{t('settings:sections.llmProvider.providers.ollama')}</SelectItem>
            <SelectItem value="anthropic">{t('settings:sections.llmProvider.providers.anthropic')}</SelectItem>
            <SelectItem value="openai">{t('settings:sections.llmProvider.providers.openai')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Ollama Settings */}
      {provider === 'ollama' && (
        <>
          <div className="space-y-2">
            <Label>{t('settings:sections.llmProvider.ollama.baseUrl')}</Label>
            <Input
              value={settings.llmOllamaBaseUrl || 'http://localhost:11434'}
              onChange={(e) => onSettingsChange({ llmOllamaBaseUrl: e.target.value })}
              placeholder="http://localhost:11434"
              className="max-w-md"
            />
          </div>

          <div className="space-y-2">
            <Label>{t('settings:sections.llmProvider.ollama.model')}</Label>
            <Select
              value={settings.llmOllamaModel || 'qwen3-30b-local:latest'}
              onValueChange={(value) => onSettingsChange({ llmOllamaModel: value })}
            >
              <SelectTrigger className="w-full max-w-md">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ollamaModels.length > 0 ? (
                  ollamaModels.map((model) => (
                    <SelectItem key={model.name} value={model.name}>
                      {model.name} ({(model.size / 1e9).toFixed(1)} GB)
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value={settings.llmOllamaModel || 'qwen3-30b-local:latest'}>
                    {settings.llmOllamaModel || 'qwen3-30b-local:latest'}
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
            <Button size="sm" variant="outline" onClick={fetchOllamaModels}>
              {t('settings:sections.llmProvider.ollama.refreshModels')}
            </Button>
          </div>
        </>
      )}

      {/* Anthropic Settings */}
      {provider === 'anthropic' && (
        <div className="space-y-2">
          <Label>{t('settings:sections.llmProvider.anthropic.model')}</Label>
          <Select
            value={settings.llmAnthropicModel || 'claude-sonnet-4-6'}
            onValueChange={(value) => onSettingsChange({ llmAnthropicModel: value })}
          >
            <SelectTrigger className="w-full max-w-md">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="claude-opus-4-6">Claude Opus 4.6</SelectItem>
              <SelectItem value="claude-sonnet-4-6">Claude Sonnet 4.6</SelectItem>
              <SelectItem value="claude-haiku-4-5-20251001">Claude Haiku 4.5</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-sm text-muted-foreground">
            {t('settings:sections.llmProvider.anthropic.apiKeyNote')}
          </p>
        </div>
      )}

      {/* OpenAI Settings */}
      {provider === 'openai' && (
        <>
          <div className="space-y-2">
            <Label>{t('settings:sections.llmProvider.openai.model')}</Label>
            <Select
              value={settings.llmOpenaiModel || 'gpt-4o'}
              onValueChange={(value) => onSettingsChange({ llmOpenaiModel: value })}
            >
              <SelectTrigger className="w-full max-w-md">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                <SelectItem value="gpt-4-turbo">GPT-4 Turbo</SelectItem>
                <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>{t('settings:sections.llmProvider.openai.baseUrl')}</Label>
            <Input
              value={settings.llmOpenaiBaseUrl || ''}
              onChange={(e) => onSettingsChange({ llmOpenaiBaseUrl: e.target.value })}
              placeholder="https://api.openai.com/v1 (optional)"
              className="max-w-md"
            />
          </div>
        </>
      )}

      {/* Test Connection */}
      <div className="flex items-center gap-2">
        <Button onClick={testConnection} disabled={isTestingConnection}>
          {isTestingConnection ? t('common:testing') : t('settings:sections.llmProvider.testConnection')}
        </Button>
        {connectionStatus && (
          <Badge variant={connectionStatus.type === 'success' ? 'success' : 'destructive'}>
            {connectionStatus.message}
          </Badge>
        )}
      </div>
    </div>
  );
}

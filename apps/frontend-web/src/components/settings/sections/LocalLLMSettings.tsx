import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { RefreshCw, Check, Circle } from 'lucide-react';
import { OllamaIcon } from '../../icons/OllamaIcon';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiRequest } from '@/lib/api-client';
import type { AppSettings } from '@/shared/types/settings';

interface LLMProvider {
  id: string;
  name: string;
  url: string;
  detected: boolean;
  installed: boolean;
  running: boolean;
  version: string;
  modelCount: number;
  models: string[];
}

interface LocalLLMSettingsProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
}

const CUSTOM_URL_ID = '__custom__';

export function LocalLLMSettings({ settings, onSettingsChange }: LocalLLMSettingsProps) {
  const { t } = useTranslation(['settings', 'common']);
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [isDetecting, setIsDetecting] = useState(false);
  const [selectedProviderId, setSelectedProviderId] = useState<string>(CUSTOM_URL_ID);
  const [ollamaModels, setOllamaModels] = useState<any[]>([]);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<{type: 'success'|'error', message: string} | null>(null);

  const detectProviders = useCallback(async () => {
    setIsDetecting(true);
    try {
      const result = await apiRequest<{ providers: LLMProvider[] }>('/settings/local-llm/detect');
      if (result.success && result.data) {
        setProviders(result.data.providers);

        // Auto-select: if current URL matches a detected provider, select it
        const currentUrl = settings.llmOllamaBaseUrl || 'http://localhost:11434';
        const matchingProvider = result.data.providers.find(
          (p) => p.detected && p.url === currentUrl
        );
        if (matchingProvider) {
          setSelectedProviderId(matchingProvider.id);
        } else {
          const anyMatch = result.data.providers.find((p) => p.url === currentUrl);
          setSelectedProviderId(anyMatch ? anyMatch.id : CUSTOM_URL_ID);
        }
      }
    } catch (error) {
      console.error('Failed to detect LLM providers:', error);
    } finally {
      setIsDetecting(false);
    }
  }, [settings.llmOllamaBaseUrl]);

  useEffect(() => {
    detectProviders();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchOllamaModels();
  }, [settings.llmOllamaBaseUrl]);

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

  const selectProvider = (providerId: string) => {
    setSelectedProviderId(providerId);
    if (providerId !== CUSTOM_URL_ID) {
      const provider = providers.find((p) => p.id === providerId);
      if (provider) {
        onSettingsChange({ ...settings, llmOllamaBaseUrl: provider.url });
      }
    }
  };

  const testConnection = async () => {
    setIsTestingConnection(true);
    setConnectionStatus(null);
    try {
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
    } catch (error) {
      setConnectionStatus({ type: 'error', message: String(error) });
    } finally {
      setIsTestingConnection(false);
    }
  };

  const getProviderStatus = (provider: LLMProvider): { label: string; variant: 'success' | 'secondary' | 'outline' } => {
    if (provider.running) {
      return {
        label: provider.modelCount > 0
          ? t('settings:sections.llmProvider.localLlms.models', { count: provider.modelCount })
          : t('settings:sections.llmProvider.localLlms.detected'),
        variant: 'success',
      };
    }
    if (provider.installed) {
      return { label: provider.version || t('settings:sections.llmProvider.localLlms.detected'), variant: 'outline' };
    }
    return { label: t('settings:sections.llmProvider.localLlms.notDetected'), variant: 'secondary' };
  };

  return (
    <div className="space-y-4">
      {/* Provider Detection */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label>{t('settings:sections.llmProvider.localLlms.provider')}</Label>
          <Button
            size="sm"
            variant="outline"
            onClick={detectProviders}
            disabled={isDetecting}
            className="gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isDetecting ? 'animate-spin' : ''}`} />
            {isDetecting
              ? t('settings:sections.llmProvider.localLlms.detecting')
              : providers.length > 0
                ? t('settings:sections.llmProvider.localLlms.detectAgain')
                : t('settings:sections.llmProvider.localLlms.detect')}
          </Button>
        </div>

        {/* Provider Cards */}
        {providers.length > 0 && (
          <div className="grid gap-2">
            {providers.filter((p) => p.detected).map((provider) => {
              const status = getProviderStatus(provider);
              return (
                <button
                  key={provider.id}
                  onClick={() => provider.detected && selectProvider(provider.id)}
                  disabled={!provider.detected}
                  className={`flex items-center justify-between rounded-md border px-3 py-2.5 text-left text-sm transition-colors ${
                    selectedProviderId === provider.id
                      ? 'border-primary bg-primary/5'
                      : provider.detected
                        ? 'border-border hover:border-primary/50 hover:bg-muted/50 cursor-pointer'
                        : 'border-border/50 opacity-50 cursor-not-allowed'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    {selectedProviderId === provider.id ? (
                      <Check className="h-4 w-4 text-primary shrink-0" />
                    ) : (
                      <Circle className={`h-4 w-4 shrink-0 ${
                        provider.running
                          ? 'text-green-500 fill-green-500'
                          : provider.installed
                            ? 'text-yellow-500 fill-yellow-500'
                            : 'text-muted-foreground/40'
                      }`} />
                    )}
                    <div className="flex flex-col">
                      <div className="flex items-center gap-1.5">
                        <OllamaIcon className="h-3.5 w-3.5 shrink-0" />
                        <span className="font-medium">{provider.name}</span>
                        {provider.version && (
                          <span className="ml-1.5 text-xs text-muted-foreground">v{provider.version}</span>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground">{provider.url}</span>
                    </div>
                  </div>
                  <Badge variant={status.variant} className="text-xs">
                    {status.label}
                  </Badge>
                </button>
              );
            })}

            {/* Custom URL option */}
            <button
              onClick={() => selectProvider(CUSTOM_URL_ID)}
              className={`flex items-center gap-2.5 rounded-md border px-3 py-2.5 text-left text-sm transition-colors ${
                selectedProviderId === CUSTOM_URL_ID
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50 hover:bg-muted/50 cursor-pointer'
              }`}
            >
              {selectedProviderId === CUSTOM_URL_ID ? (
                <Check className="h-4 w-4 text-primary shrink-0" />
              ) : (
                <Circle className="h-4 w-4 text-muted-foreground/40 shrink-0" />
              )}
              <span className="font-medium">{t('settings:sections.llmProvider.localLlms.customUrl')}</span>
            </button>
          </div>
        )}
      </div>

      {/* Base URL Input */}
      <div className="space-y-2">
        <Label>{t('settings:sections.llmProvider.ollama.baseUrl')}</Label>
        <Input
          value={settings.llmOllamaBaseUrl || 'http://localhost:11434'}
          onChange={(e) => {
            onSettingsChange({ ...settings, llmOllamaBaseUrl: e.target.value });
            const matchingProvider = providers.find((p) => p.url === e.target.value);
            setSelectedProviderId(matchingProvider ? matchingProvider.id : CUSTOM_URL_ID);
          }}
          placeholder="http://localhost:11434"
          className="max-w-md"
          readOnly={selectedProviderId !== CUSTOM_URL_ID && providers.length > 0}
        />
      </div>

      <div className="space-y-2">
        <Label>{t('settings:sections.llmProvider.ollama.model')}</Label>
        <Select
          value={settings.llmOllamaModel || 'qwen3-30b-local:latest'}
          onValueChange={(value) => onSettingsChange({ ...settings, llmOllamaModel: value })}
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

      <div className="flex items-center gap-2">
        <Button onClick={testConnection} disabled={isTestingConnection} size="sm">
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

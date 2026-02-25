import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ArrowUpCircle,
  Check,
  ChevronDown,
  ChevronRight,
  Download,
  Eye,
  EyeOff,
  Loader2,
  LogIn,
  Trash2,
  X,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { cn } from '../../../lib/utils';
import { OpenAIIcon } from '../../icons/OpenAIIcon';
import { GeminiIcon } from '../../icons/GeminiIcon';
import type { CLIAccountStatus } from '../../../shared/types';

interface CLIAccountCardProps {
  cli: 'codex' | 'gemini';
  status: CLIAccountStatus | null;
  isLoading: boolean;
  onImport: () => void;
  onStartLogin: () => void;
  onSetApiKey: (key: string) => void;
  onRemove: () => void;
  onInstall: () => Promise<void>;
}

export function CLIAccountCard({
  cli,
  status,
  isLoading,
  onImport,
  onStartLogin,
  onSetApiKey,
  onRemove,
  onInstall,
}: CLIAccountCardProps) {
  const { t } = useTranslation('settings');
  const { t: tCommon } = useTranslation('common');

  const [expandedApiKey, setExpandedApiKey] = useState(false);
  const [apiKeyValue, setApiKeyValue] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoginPolling, setIsLoginPolling] = useState(false);
  const [isInstalling, setIsInstalling] = useState(false);

  const Icon = cli === 'codex' ? OpenAIIcon : GeminiIcon;
  const cliName = t(`integrations.${cli}.name`);
  const cliDescription = t(`integrations.${cli}.description`);
  const installHint = t(`integrations.${cli}.installHint`);

  const hasUpdate = status?.installed && status?.latestVersion && status?.version !== status?.latestVersion;

  const getAuthMethodLabel = () => {
    if (!status?.authMethod) return null;
    if (cli === 'codex') {
      return status.authMethod === 'oauth'
        ? t('integrations.codex.viaOAuth')
        : t('integrations.codex.viaApiKey');
    }
    return status.authMethod === 'google_login'
      ? t('integrations.gemini.viaGoogleLogin')
      : t('integrations.gemini.viaApiKey');
  };

  const handleSubmitApiKey = async () => {
    if (!apiKeyValue.trim() || apiKeyValue.trim().length < 5) return;
    setIsSubmitting(true);
    try {
      onSetApiKey(apiKeyValue.trim());
      setApiKeyValue('');
      setExpandedApiKey(false);
      setShowApiKey(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStartLogin = () => {
    setIsLoginPolling(true);
    onStartLogin();
    // Auto-reset after 3 min timeout
    setTimeout(() => setIsLoginPolling(false), 180000);
  };

  const handleInstall = async () => {
    setIsInstalling(true);
    try {
      await onInstall();
    } finally {
      setIsInstalling(false);
    }
  };

  // Reset login polling when auth succeeds
  if (isLoginPolling && status?.authenticated) {
    setIsLoginPolling(false);
  }

  // Not installed state
  if (!status || !status.installed) {
    return (
      <div className="rounded-lg border border-dashed border-border p-3">
        <div className="flex items-center gap-3">
          <div className="h-7 w-7 rounded-full flex items-center justify-center bg-muted text-muted-foreground shrink-0">
            <Icon className="h-3.5 w-3.5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground">{cliName}</span>
              <span className="text-xs bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
                {t('integrations.notInstalled')}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">{cliDescription}</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleInstall}
            disabled={isInstalling}
            className="gap-1 h-7 text-xs shrink-0"
          >
            {isInstalling ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Download className="h-3 w-3" />
            )}
            {isInstalling ? t('integrations.installing') : t('integrations.install')}
          </Button>
        </div>
        <div className="mt-2 ml-10">
          <code className="text-xs bg-muted px-2 py-1 rounded font-mono text-muted-foreground">
            {installHint}
          </code>
        </div>
      </div>
    );
  }

  // Installed state
  return (
    <div
      className={cn(
        'rounded-lg border transition-colors',
        status.authenticated
          ? 'border-success/30 bg-success/5'
          : 'border-border bg-background'
      )}
    >
      <div className="flex items-center justify-between p-3">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'h-7 w-7 rounded-full flex items-center justify-center shrink-0',
              status.authenticated
                ? 'bg-success/20 text-success'
                : 'bg-muted text-muted-foreground'
            )}
          >
            <Icon className="h-3.5 w-3.5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium text-foreground">{cliName}</span>
              {status.version && (
                <span className="text-xs text-muted-foreground font-mono">
                  {status.version}
                </span>
              )}
              {status.authenticated ? (
                <span className="text-xs bg-success/20 text-success px-1.5 py-0.5 rounded flex items-center gap-1">
                  <Check className="h-3 w-3" />
                  {t('integrations.authenticated')}
                </span>
              ) : (
                <span className="text-xs bg-warning/20 text-warning px-1.5 py-0.5 rounded">
                  {t('integrations.needsAuth')}
                </span>
              )}
              {hasUpdate && (
                <span className="text-xs bg-blue-500/20 text-blue-600 dark:text-blue-400 px-1.5 py-0.5 rounded flex items-center gap-1">
                  <ArrowUpCircle className="h-3 w-3" />
                  {t('integrations.updateAvailable')}
                </span>
              )}
            </div>
            {status.authenticated && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-muted-foreground">{getAuthMethodLabel()}</span>
                {status.email && (
                  <span className="text-xs text-muted-foreground">{status.email}</span>
                )}
              </div>
            )}
            {status.tokenExpiresAt && (
              <span className="text-xs text-muted-foreground ml-2">
                {t(`integrations.${cli}.tokenExpires`)}: {new Date(status.tokenExpiresAt).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1">
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : (
            <>
              {hasUpdate && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleInstall}
                  disabled={isInstalling}
                  className="gap-1 h-7 text-xs"
                >
                  {isInstalling ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <ArrowUpCircle className="h-3 w-3" />
                  )}
                  {isInstalling ? t('integrations.updating') : t('integrations.update')}
                </Button>
              )}
              {!status.authenticated && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleStartLogin}
                    disabled={isLoginPolling}
                    className="gap-1 h-7 text-xs"
                  >
                    {isLoginPolling ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <LogIn className="h-3 w-3" />
                    )}
                    {isLoginPolling
                      ? t('integrations.waitingForAuth')
                      : t('integrations.loginInTerminal')}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onImport}
                    className="gap-1 h-7 text-xs"
                    title={t(`integrations.${cli}.importHint`)}
                  >
                    <Download className="h-3 w-3" />
                    {t('integrations.importCredentials')}
                  </Button>
                </>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  setExpandedApiKey(!expandedApiKey);
                  setApiKeyValue('');
                  setShowApiKey(false);
                }}
                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                title={t('integrations.apiKeyEntry')}
              >
                {expandedApiKey ? (
                  <ChevronDown className="h-3 w-3" />
                ) : (
                  <ChevronRight className="h-3 w-3" />
                )}
              </Button>
              {status.authenticated && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onRemove}
                  className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                  title={t('integrations.disconnect')}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Login hint when polling */}
      {isLoginPolling && (
        <div className="px-3 pb-3 pt-0">
          <div className="bg-muted/30 rounded-lg p-3 text-xs text-muted-foreground">
            {t(`integrations.${cli}.loginHint`)}
          </div>
        </div>
      )}

      {/* Credentials detected hint (when not authenticated but CLI credential files exist) */}
      {!status.authenticated && !isLoginPolling && (
        <div className="px-3 pb-2 pt-0">
          <span className="text-xs text-muted-foreground">
            {t('integrations.credentialsDetected')}: <code className="font-mono text-xs">~/.{cli}/</code>
          </span>
        </div>
      )}

      {/* Expandable API key entry */}
      {expandedApiKey && (
        <div className="px-3 pb-3 pt-0 border-t border-border/50 mt-0">
          <div className="bg-muted/30 rounded-lg p-3 mt-3 space-y-3">
            <Label className="text-xs font-medium text-muted-foreground">
              {t('integrations.apiKeyEntry')}
            </Label>
            <div className="relative">
              <Input
                type={showApiKey ? 'text' : 'password'}
                placeholder={t('integrations.apiKeyPlaceholder')}
                value={apiKeyValue}
                onChange={(e) => setApiKeyValue(e.target.value)}
                className="pr-10 font-mono text-xs h-8"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSubmitApiKey();
                  if (e.key === 'Escape') {
                    setExpandedApiKey(false);
                    setApiKeyValue('');
                  }
                }}
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showApiKey ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
              </button>
            </div>
            <div className="flex items-center justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setExpandedApiKey(false);
                  setApiKeyValue('');
                  setShowApiKey(false);
                }}
                className="h-7 text-xs"
              >
                <X className="h-3 w-3 mr-1" />
                {tCommon('buttons.cancel')}
              </Button>
              <Button
                size="sm"
                onClick={handleSubmitApiKey}
                disabled={!apiKeyValue.trim() || apiKeyValue.trim().length < 5 || isSubmitting}
                className="h-7 text-xs gap-1"
              >
                {isSubmitting ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Check className="h-3 w-3" />
                )}
                {t('integrations.saveToken')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

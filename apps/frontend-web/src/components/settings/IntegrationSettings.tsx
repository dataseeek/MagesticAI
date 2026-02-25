import { useTranslation } from 'react-i18next';
import { Key } from 'lucide-react';
import { SettingsSection } from './SettingsSection';

/**
 * Integrations settings placeholder - content moved to LLM Providers page.
 * Claude Accounts, Auto-Switch, and API Keys are now under LLM Providers.
 */
export function IntegrationSettings() {
  const { t } = useTranslation('settings');

  return (
    <SettingsSection
      title={t('sections.integrations.title')}
      description={t('sections.integrations.description')}
    >
      <div className="rounded-lg border border-dashed border-border p-8 text-center">
        <Key className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">
          {t('integrations.comingSoon')}
        </p>
      </div>
    </SettingsSection>
  );
}

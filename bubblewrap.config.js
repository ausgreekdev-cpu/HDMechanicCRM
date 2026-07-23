const { BubblewrapCli } = require('@nicedash/pwabuilder-cli');

const config = {
  appPackageId: 'com.hdmechanic.crm',
  appName: 'HDMechanicCRM',
  shortName: 'HDMechanic',
  themeColor: '#003366',
  backgroundColor: '#003366',
  startUrl: '/',
  scope: '/',
  display: 'standalone',
  signing: {
    keystore: 'android-release.keystore',
    keystorePassword: process.env.KEYSTORE_PASSWORD || 'changeme',
    keyAlias: 'hdmechanic',
    keyPassword: process.env.KEY_PASSWORD || 'changeme',
  },
  icon: './app/static/icons/icon-512.png',
  screenshots: [],
  categories: ['business', 'productivity'],
  description: 'All-in-one mechanic shop & scrap metal business CRM',
  versionCode: 1,
  versionName: '1.0.0',
  minSdkVersion: 21,
  targetSdkVersion: 33,
  permissions: ['INTERNET', 'ACCESS_NETWORK_STATE'],
  host: {
    host: 'localhost:8000',
    backgroundColor: '#003366',
    themeColor: '#003366',
  },
  fallbackType: 'custom',
  customBuildSteps: [],
};

module.exports = config;

export interface HotelDataRuntimeConfig {
  syncfusionLicenseKey: string;
}

declare global {
  interface Window {
    __HOTELDATA_CONFIG__?: Partial<HotelDataRuntimeConfig>;
  }
}

export function getRuntimeConfig(): HotelDataRuntimeConfig {
  return {
    syncfusionLicenseKey: window.__HOTELDATA_CONFIG__?.syncfusionLicenseKey?.trim() ?? '',
  };
}

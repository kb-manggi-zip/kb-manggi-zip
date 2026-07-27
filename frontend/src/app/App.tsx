import React from 'react';
import { AppProvider, useApp } from '../store';
import type { Branch } from '../api/types';

import HomeEntry from '../screens/HomeEntry';
import ContractInput from '../screens/ContractInput';
import CalcLoading from '../screens/CalcLoading';
import CompareTable from '../screens/CompareTable';
import RegionList from '../screens/RegionList';
import RegionListMonthly from '../screens/RegionListMonthly';
import RenewalChecklist from '../screens/RenewalChecklist';
import DayPlayer from '../screens/DayPlayer';
import SavedMoneyPlayer from '../screens/SavedMoneyPlayer';
import FinancePackage from '../screens/FinancePackage';
import ReservationSheet from '../screens/ReservationSheet';
import SaveReminder from '../screens/SaveReminder';
import DecisionReportScreen from '../screens/DecisionReportScreen';

function Router() {
  const { state } = useApp();
  const { screen, selectedBranch, contract } = state;

  switch (screen) {
    case 'SC-01': return <HomeEntry />;
    case 'SC-02': return <ContractInput />;
    case 'SC-12': return <CalcLoading />;
    case 'SC-03': return <CompareTable />;
    case 'SC-04':
      // 월세 사용자가 이사를 선택했으면 SC-05로 분기
      if (contract?.type === '월세' && selectedBranch === '이사') return <RegionListMonthly />;
      return <RegionList />;
    case 'SC-05': return <RegionListMonthly />;
    case 'SC-06': return <RenewalChecklist />;
    case 'SC-07': return <DayPlayer />;
    case 'SC-08': return <SavedMoneyPlayer />;
    case 'SC-09': return <FinancePackage />;
    case 'SC-10': return <ReservationSheet />;
    case 'SC-11': return <SaveReminder />;
    case 'SC-13': return <DecisionReportScreen />;
    default: return <HomeEntry />;
  }
}

export default function App() {
  return (
    <AppProvider>
      <div
        className="min-h-dvh bg-[#F0EDE8] flex items-start justify-center"
        style={{ fontFamily: "'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}
      >
        <Router />
      </div>
    </AppProvider>
  );
}

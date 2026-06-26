export interface User {
    id: number;
    email: string;
    role: string;
    firm_logo?: string;
    firm_name?: string;
    gst_rate?: number;
    is_disabled?: boolean;
}

export interface Client {
    id: number;
    name: string;
    email?: string;
    phone?: string;
    notes?: string;
    created_at: string;
}

export interface Matter {
    id: number;
    client_id: number;
    case_number?: string;
    title: string;
    court?: string;
    judge?: string;
    opponent_name?: string;
    opposing_advocate?: string;
    status: string;
    facts?: string;
    cnr_number?: string;
    is_locked: boolean;
    created_at: string;
}

export interface Document {
    id: number;
    matter_id?: number;
    original_name: string;
    stored_uuid: string;
    file_hash: string;
    status: string;
    uploaded_at: string;
}

export interface Schedule {
    id: number;
    matter_id: number;
    title: string;
    schedule_type: string;
    target_date: string;
    notes?: string;
    is_completed: boolean;
}

export interface TimeEntry {
    id: number;
    matter_id: number;
    description: string;
    hours: number;
    rate_per_hour: number;
    date: string;
    amount?: string;
}

export interface Invoice {
    id: number;
    client_id: number;
    matter_id?: number;
    invoice_number: string;
    total_amount: string;
    gst_amount: string;
    grand_total: string;
    status: string;
    notes?: string;
    created_at: string;
}

import { Component, OnInit } from '@angular/core';
import { Http } from '@angular/http';

import { DartService } from './dart.service';

@Component({
    selector: 'app-root',
    templateUrl: './dart-list.component.html',
    styleUrls: ['./app.component.css'],
    providers: [DartService]
})
export class DartListComponent implements OnInit {
    records;

    constructor(private dartService: DartService) {}

    ngOnInit(): void {
        this.records = this.dartService.getRecords().map(v => v['records']);
    }
}

import { Component, OnInit } from '@angular/core';
import { Http } from '@angular/http';

import { DartService } from './dart.service';

@Component({
    selector: 'app-root',
    templateUrl: './listdart.component.html',
    styleUrls: ['./app.component.css'],
    providers: [DartService]
})
export class ListDartComponent implements OnInit {
    records;

    constructor(private dartService: DartService) {}

    ngOnInit(): void {
        this.records = this.dartService.getRecords().map(v => v['records']);
    }
}

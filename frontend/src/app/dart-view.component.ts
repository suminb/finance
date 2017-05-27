import { Component, Input, OnInit } from '@angular/core';
import { ActivatedRoute, Params } from '@angular/router';
import { Http } from '@angular/http';
import { Observable } from 'rxjs/Observable';
import 'rxjs/add/operator/map';
import 'rxjs/add/operator/switchMap';

import { DartService } from './dart.service';
import { DartReport } from './dart.model';

@Component({
    selector: 'app-root',
    templateUrl: './dart-view.component.html',
    styleUrls: ['./app.component.css'],
    providers: [DartService]
})
export class DartViewComponent implements OnInit {
    report;

    constructor(
        private dartService: DartService,
        private route: ActivatedRoute) {
    }

    ngOnInit(): void {
        this.route.params
            .map(params => params['id'])
            .switchMap(id => this.dartService.getRecord(id))
            .subscribe(report => this.report = report);
    }
}

